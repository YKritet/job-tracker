import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .search.base import JobResult

_DB_PATH = Path("results/applier.db")


def set_db_path(p: Path) -> None:
    global _DB_PATH
    _DB_PATH = p


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            url       TEXT PRIMARY KEY,
            title     TEXT NOT NULL,
            company   TEXT NOT NULL,
            location  TEXT NOT NULL,
            contract  TEXT NOT NULL DEFAULT '',
            platform  TEXT NOT NULL,
            tags      TEXT NOT NULL DEFAULT '[]',
            poste     TEXT NOT NULL DEFAULT '',
            domain    TEXT NOT NULL DEFAULT '',
            skills    TEXT NOT NULL DEFAULT '[]',
            pulled_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS tracking (
            url          TEXT PRIMARY KEY,
            status       TEXT NOT NULL DEFAULT '',
            applied_date TEXT NOT NULL DEFAULT '',
            notes        TEXT NOT NULL DEFAULT '',
            updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS source_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT NOT NULL,
            checked_at TEXT NOT NULL DEFAULT (datetime('now')),
            jobs_found INTEGER NOT NULL DEFAULT 0,
            status     TEXT NOT NULL DEFAULT 'ok'
        );
        CREATE TABLE IF NOT EXISTS watchlist_snap (
            company      TEXT PRIMARY KEY,
            careers_url  TEXT NOT NULL DEFAULT '',
            content_hash TEXT NOT NULL DEFAULT '',
            last_checked TEXT NOT NULL DEFAULT (datetime('now')),
            last_status  TEXT NOT NULL DEFAULT 'ok'
        );
        """)
        # Migrate existing DBs that predate poste/domain/skills columns
        for col, default in (("poste", "''"), ("domain", "''"), ("skills", "'[]'")):
            try:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT NOT NULL DEFAULT {default}")
            except sqlite3.OperationalError:
                pass  # column already exists


def upsert_jobs(results: list[JobResult]) -> None:
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO jobs (url, title, company, location, contract, platform, tags, poste, domain, skills, pulled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title, company=excluded.company,
                location=excluded.location, contract=excluded.contract,
                platform=excluded.platform, tags=excluded.tags,
                poste=excluded.poste, domain=excluded.domain,
                skills=excluded.skills, pulled_at=excluded.pulled_at
            """,
            [
                (
                    r.url, r.title, r.company, r.location, r.contract,
                    r.platform, json.dumps(r.tags, ensure_ascii=False),
                    r.poste, r.domain,
                    json.dumps(r.skills, ensure_ascii=False),
                    r.pulled_at,
                )
                for r in results
            ],
        )


def get_distinct_skills() -> list[str]:
    """Return all distinct skill labels that appear in at least one job."""
    with get_conn() as conn:
        rows = conn.execute("SELECT skills FROM jobs WHERE skills != '[]'").fetchall()
    seen: set[str] = set()
    result: list[str] = []
    for row in rows:
        for skill in json.loads(row["skills"]):
            if skill not in seen:
                seen.add(skill)
                result.append(skill)
    return sorted(result)


def get_all_jobs(max_age_days: int = 0) -> list[dict]:
    cutoff_clause = f"AND j.pulled_at >= date('now', '-{max_age_days} days')" if max_age_days > 0 else ""
    with get_conn() as conn:
        rows = conn.execute(f"""
            SELECT j.*,
                   COALESCE(t.status,       '') AS status,
                   COALESCE(t.applied_date, '') AS applied_date,
                   COALESCE(t.notes,        '') AS notes
            FROM jobs j
            LEFT JOIN tracking t ON j.url = t.url
            WHERE 1=1 {cutoff_clause}
            ORDER BY j.pulled_at DESC, j.title
        """).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"])
        d["skills"] = json.loads(d.get("skills") or "[]")
        out.append(d)
    return out


def export_jobs_json(path: Path) -> None:
    """Write all jobs (without tracking) to a JSON file for sharing."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY pulled_at DESC, title").fetchall()
    data = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"])
        d["skills"] = json.loads(d.get("skills") or "[]")
        data.append(d)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def import_from_json(path: Path) -> int:
    """Import jobs from a JSON file into the DB. Returns number of rows processed."""
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO jobs (url, title, company, location, contract, platform, tags, poste, domain, skills, pulled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title, company=excluded.company,
                location=excluded.location, contract=excluded.contract,
                platform=excluded.platform, tags=excluded.tags,
                poste=excluded.poste, domain=excluded.domain,
                skills=excluded.skills, pulled_at=excluded.pulled_at
            """,
            [
                (
                    r["url"], r["title"], r["company"], r["location"],
                    r.get("contract", ""), r["platform"],
                    json.dumps(r.get("tags", []), ensure_ascii=False),
                    r.get("poste", ""), r.get("domain", ""),
                    json.dumps(r.get("skills", []), ensure_ascii=False),
                    r.get("pulled_at", ""),
                )
                for r in data
            ],
        )
    return len(data)


def update_tracking(url: str, status: str | None, applied_date: str | None, notes: str | None) -> None:
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM tracking WHERE url=?", (url,)).fetchone()
        if existing:
            merged = dict(existing)
            if status       is not None: merged["status"]       = status
            if applied_date is not None: merged["applied_date"] = applied_date
            if notes        is not None: merged["notes"]        = notes
            conn.execute(
                "UPDATE tracking SET status=?, applied_date=?, notes=?, updated_at=datetime('now') WHERE url=?",
                (merged["status"], merged["applied_date"], merged["notes"], url),
            )
        else:
            conn.execute(
                "INSERT INTO tracking (url, status, applied_date, notes) VALUES (?,?,?,?)",
                (url, status or "", applied_date or "", notes or ""),
            )


def get_watchlist_snap(company: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM watchlist_snap WHERE company=?", (company,)
        ).fetchone()
    return dict(row) if row else None


def set_watchlist_snap(
    company: str, careers_url: str, content_hash: str, status: str = "ok"
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO watchlist_snap (company, careers_url, content_hash, last_checked, last_status)
            VALUES (?, ?, ?, datetime('now'), ?)
            ON CONFLICT(company) DO UPDATE SET
                careers_url=excluded.careers_url,
                content_hash=excluded.content_hash,
                last_checked=excluded.last_checked,
                last_status=excluded.last_status
            """,
            (company, careers_url, content_hash, status),
        )


def get_watchlist_coverage() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT company, careers_url, last_checked, last_status, content_hash "
            "FROM watchlist_snap ORDER BY last_checked DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def log_source_check(source: str, jobs_found: int, status: str = "ok") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO source_log (source, jobs_found, status) VALUES (?, ?, ?)",
            (source, jobs_found, status),
        )


def purge_old_jobs(max_age_days: int) -> int:
    """Delete jobs whose pulled_at is older than max_age_days. Returns deleted count."""
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM jobs WHERE pulled_at < date('now', ?)",
            (f"-{max_age_days} days",),
        )
        return result.rowcount


def get_coverage() -> list[dict]:
    """Return per-source summary: last checked, total jobs found, check count."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT source,
                   MAX(checked_at) AS last_checked,
                   SUM(jobs_found) AS total_found,
                   COUNT(*)        AS checks,
                   MAX(status)     AS last_status
            FROM source_log
            GROUP BY source
            ORDER BY last_checked DESC
        """).fetchall()
    return [dict(r) for r in rows]
