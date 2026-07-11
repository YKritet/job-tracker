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
        """)
        # Migrate existing DBs that predate poste/domain columns
        for col in ("poste", "domain"):
            try:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # column already exists


def upsert_jobs(results: list[JobResult]) -> None:
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO jobs (url, title, company, location, contract, platform, tags, poste, domain, pulled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title, company=excluded.company,
                location=excluded.location, contract=excluded.contract,
                platform=excluded.platform, tags=excluded.tags,
                poste=excluded.poste, domain=excluded.domain,
                pulled_at=excluded.pulled_at
            """,
            [
                (
                    r.url, r.title, r.company, r.location, r.contract,
                    r.platform, json.dumps(r.tags, ensure_ascii=False),
                    r.poste, r.domain, r.pulled_at,
                )
                for r in results
            ],
        )


def get_all_jobs() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT j.*,
                   COALESCE(t.status,       '') AS status,
                   COALESCE(t.applied_date, '') AS applied_date,
                   COALESCE(t.notes,        '') AS notes
            FROM jobs j
            LEFT JOIN tracking t ON j.url = t.url
            ORDER BY j.pulled_at DESC, j.title
        """).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"])
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
            INSERT INTO jobs (url, title, company, location, contract, platform, tags, poste, domain, pulled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title, company=excluded.company,
                location=excluded.location, contract=excluded.contract,
                platform=excluded.platform, tags=excluded.tags,
                poste=excluded.poste, domain=excluded.domain,
                pulled_at=excluded.pulled_at
            """,
            [
                (
                    r["url"], r["title"], r["company"], r["location"],
                    r.get("contract", ""), r["platform"],
                    json.dumps(r.get("tags", []), ensure_ascii=False),
                    r.get("poste", ""), r.get("domain", ""),
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


def log_source_check(source: str, jobs_found: int, status: str = "ok") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO source_log (source, jobs_found, status) VALUES (?, ?, ?)",
            (source, jobs_found, status),
        )


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
