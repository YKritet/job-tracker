import os
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Annotated
from dotenv import load_dotenv
import typer
from rich.console import Console

from .search.linkedin import LinkedInSearcher
from .search.francetravail import FranceTravailSearcher
from .search.remoteok import RemoteOKSearcher
from .search.base import JobResult, auto_tag
from . import db, export

load_dotenv()

app = typer.Typer(help="Job search CLI — finds and lists job URLs across platforms.")
console = Console()

# Keywords that flag alternance/apprentissage — excluded by default
_ALTERNANCE_KW = (
    "alternance", "alternant", "apprentissage", "apprenti",
    "contrat d'apprentissage", "en alternance", "work-study",
)


def _is_alternance(r: JobResult) -> bool:
    text = (r.title + " " + r.contract).lower()
    return any(kw in text for kw in _ALTERNANCE_KW)


@app.command()
def search(
    profile: Annotated[Path, typer.Option("--profile", "-p")] = Path("profiles/hamza.toml"),
    platforms: Annotated[str, typer.Option(help="linkedin,francetravail,remoteok")] = "linkedin,francetravail,remoteok",
    locations: Annotated[str, typer.Option(help="Location labels from profile, or 'all'")] = "all",
    count: Annotated[int, typer.Option(help="Max results per query")] = 25,
    output: Annotated[str, typer.Option(help="Output file (.html/.xlsx/.csv/.json)")] = "results/jobs.html",
    fmt: Annotated[str, typer.Option("--format", help="Force format: html, xlsx, csv, json")] = "",
    no_filter: Annotated[bool, typer.Option("--no-filter", help="Disable alternance filtering")] = False,
):
    """Search for jobs and export to a standalone HTML tracker (or other format)."""

    if not profile.exists():
        console.print(f"[red]Profile not found: {profile}[/red]")
        raise typer.Exit(1)

    with profile.open("rb") as f:
        cfg = tomllib.load(f)

    search_cfg = cfg.get("search", {})
    all_locs = search_cfg.get("locations", [])
    loc_lookup = {loc["label"].lower(): loc for loc in all_locs}

    active_locs = all_locs if locations.strip().lower() == "all" else [
        loc_lookup.get(l.strip().lower()) for l in locations.split(",")
        if loc_lookup.get(l.strip().lower())
    ]
    if not active_locs:
        console.print(f"[red]No matching locations. Available: {list(loc_lookup.keys())}[/red]")
        raise typer.Exit(1)

    active_platforms = {p.strip().lower() for p in platforms.split(",")}
    fr_roles = search_cfg.get("roles_fr", [])
    en_roles = search_cfg.get("roles_en", [])
    li_at = os.getenv("LINKEDIN_LI_AT", "")
    pulled_at = datetime.now().strftime("%Y-%m-%d")

    all_results: list[JobResult] = []
    seen_urls: set[str] = set()
    skipped_alt = 0

    def add_results(new: list[JobResult], label: str) -> None:
        nonlocal skipped_alt
        for r in new:
            if r.url in seen_urls:
                continue
            if not no_filter and _is_alternance(r):
                skipped_alt += 1
                continue
            r.pulled_at = pulled_at
            r.tags = auto_tag(r.title, r.location, r.contract)
            seen_urls.add(r.url)
            all_results.append(r)
        console.print(f"    +{len([r for r in new if r.url in seen_urls])} ({label})")

    for loc in active_locs:
        country = loc.get("country", "FR")
        label = loc["label"]
        roles = en_roles if country != "FR" else fr_roles
        ft_location = loc.get("ft_location", "")
        console.print(f"\n[cyan]── {label}[/cyan]")

        for role in roles:
            if "linkedin" in active_platforms:
                try:
                    raw = LinkedInSearcher(li_at).search(role, label, count)
                    add_results(raw, f"LinkedIn · {role[:40]}")
                except Exception as e:
                    console.print(f"  [red]LinkedIn:[/red] {e}")

            if "francetravail" in active_platforms and country == "FR":
                try:
                    raw = FranceTravailSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"FranceTravail · {role[:40]}")
                except Exception as e:
                    console.print(f"  [red]FranceTravail:[/red] {e}")

    if "remoteok" in active_platforms:
        console.print(f"\n[cyan]── Remote (global)[/cyan]")
        for tag in ["sales", "marketing", "it", "business-development", "technical-account-manager"]:
            try:
                raw = RemoteOKSearcher().search(tag, "remote", count)
                add_results(raw, f"RemoteOK · {tag}")
            except Exception as e:
                console.print(f"  [red]RemoteOK:[/red] {e}")

    console.print(f"\n[bold green]{len(all_results)} jobs found[/bold green]", end="")
    if skipped_alt:
        console.print(f" [dim]({skipped_alt} alternance filtered out)[/dim]")
    else:
        console.print()

    if not all_results:
        console.print("[yellow]No results.[/yellow]")
        raise typer.Exit(0)

    # Always persist to DB
    db.init_db()
    db.upsert_jobs(all_results)
    console.print(f"[dim]  → saved to DB ({db._DB_PATH})[/dim]")

    # Always export jobs.json for sharing via GitHub
    json_path = Path("results/jobs.json")
    db.export_jobs_json(json_path)
    console.print(f"[dim]  → exported {json_path} (commit + push to share with Hamza)[/dim]")

    # Optional file export
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ext = fmt or out_path.suffix.lstrip(".")
        if ext == "csv":
            export.to_csv(all_results, out_path)
        elif ext == "json":
            export.to_json(all_results, out_path)
        elif ext in ("md", "markdown"):
            export.to_markdown(all_results, out_path)
        elif ext in ("xlsx", "excel"):
            export.to_excel(all_results, out_path)
        else:
            export.to_html(all_results, out_path)

    console.print("[green]Run [bold]applier serve[/bold] to open the tracker.[/green]")


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port")] = 5050,
    open_browser: Annotated[bool, typer.Option("--open/--no-open")] = True,
):
    """Start the job tracker web UI (FastAPI + SQLite)."""
    import uvicorn
    import webbrowser
    import threading

    db.init_db()
    url = f"http://{host}:{port}"
    console.print(f"[green]Job Tracker → {url}[/green]")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    uvicorn.run("applier.server:app", host=host, port=port, reload=False, log_level="warning")


@app.command()
def platforms():
    """List supported platforms."""
    console.print("  [green]linkedin[/green]      — LinkedIn guest API (no auth)")
    console.print("  [green]francetravail[/green] — France Travail (FR only)")
    console.print("  [green]remoteok[/green]      — RemoteOK public API (remote, global)")
