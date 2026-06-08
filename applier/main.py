import os
import tomllib
from pathlib import Path
from typing import Annotated
from dotenv import load_dotenv
import typer
from rich.console import Console

from .search.linkedin import LinkedInSearcher
from .search.francetravail import FranceTravailSearcher
from .search.remoteok import RemoteOKSearcher
from .search.base import JobResult
from . import export

load_dotenv()

app = typer.Typer(help="Job search CLI — lists job URLs across platforms based on a candidate profile.")
console = Console()


@app.command()
def search(
    profile: Annotated[Path, typer.Option("--profile", "-p", help="Candidate TOML profile")] = Path("profiles/hamza.toml"),
    platforms: Annotated[str, typer.Option(help="Comma-separated: linkedin,francetravail,remoteok")] = "linkedin,francetravail,remoteok",
    locations: Annotated[str, typer.Option(help="Comma-separated location labels from profile, or 'all'")] = "all",
    count: Annotated[int, typer.Option(help="Max results per query")] = 25,
    output: Annotated[str, typer.Option(help="Output file (auto-detects .md/.csv/.json)")] = "results/results.md",
    fmt: Annotated[str, typer.Option("--format", help="Force format: md, csv, json, table")] = "",
):
    """Search for jobs matching the candidate profile and output a list of URLs."""

    if not profile.exists():
        console.print(f"[red]Profile not found: {profile}[/red]")
        raise typer.Exit(1)

    with profile.open("rb") as f:
        cfg = tomllib.load(f)

    candidate = cfg.get("candidate", {})
    search_cfg = cfg.get("search", {})
    aspirations = cfg.get("aspirations", {})

    console.print(f"\n[bold]Candidate:[/bold] {candidate.get('name', '?')}")
    console.print(f"[bold]Goal:[/bold] {aspirations.get('summary', '').strip()[:120]}…\n")

    all_locs = search_cfg.get("locations", [])
    loc_lookup = {loc["label"].lower(): loc for loc in all_locs}

    if locations.strip().lower() == "all":
        active_locs = all_locs
    else:
        active_locs = [loc_lookup.get(l.strip().lower()) for l in locations.split(",")]
        active_locs = [l for l in active_locs if l]

    if not active_locs:
        console.print(f"[red]No matching locations. Available: {list(loc_lookup.keys())}[/red]")
        raise typer.Exit(1)

    active_platforms = {p.strip().lower() for p in platforms.split(",")}
    fr_roles = search_cfg.get("roles_fr", [])
    en_roles = search_cfg.get("roles_en", [])
    li_at = os.getenv("LINKEDIN_LI_AT", "")

    all_results: list[JobResult] = []
    seen_urls: set[str] = set()

    def add_results(new: list[JobResult], label: str) -> int:
        fresh = [r for r in new if r.url not in seen_urls]
        seen_urls.update(r.url for r in fresh)
        all_results.extend(fresh)
        console.print(f"    +{len(fresh)} new ({label})")
        return len(fresh)

    # Per-location searches
    for loc in active_locs:
        country = loc.get("country", "FR")
        label = loc["label"]
        roles = en_roles if country != "FR" else fr_roles
        geo_id = loc.get("linkedin_geo")
        ft_location = loc.get("ft_location", "")

        console.print(f"\n[cyan]── {label} ({country})[/cyan]")

        for role in roles:
            if "linkedin" in active_platforms:
                try:
                    searcher = LinkedInSearcher(li_at)
                    geo_label = label if not geo_id else label
                    raw = searcher.search(role, geo_label, count)
                    add_results(raw, f"LinkedIn · {role[:40]}")
                except Exception as e:
                    console.print(f"  [red]LinkedIn error:[/red] {e}")

            if "francetravail" in active_platforms and country == "FR":
                try:
                    searcher = FranceTravailSearcher()
                    raw = searcher.search(role, ft_location or label, count)
                    add_results(raw, f"FranceTravail · {role[:40]}")
                except Exception as e:
                    console.print(f"  [red]France Travail error:[/red] {e}")

    # RemoteOK — run once across all EN roles (platform is global)
    if "remoteok" in active_platforms:
        console.print(f"\n[cyan]── Remote (global)[/cyan]")
        remote_tags = ["sales", "marketing", "it", "business-development", "technical-account-manager"]
        for tag in remote_tags:
            try:
                searcher = RemoteOKSearcher()
                raw = searcher.search(tag, "remote", count)
                add_results(raw, f"RemoteOK · {tag}")
            except Exception as e:
                console.print(f"  [red]RemoteOK error:[/red] {e}")

    console.print(f"\n[bold green]Total unique results: {len(all_results)}[/bold green]\n")

    if not all_results:
        console.print("[yellow]No results found.[/yellow]")
        raise typer.Exit(0)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ext = fmt or out_path.suffix.lstrip(".")
    if ext == "csv":
        export.to_csv(all_results, out_path)
    elif ext == "json":
        export.to_json(all_results, out_path)
    elif ext in ("md", "markdown"):
        export.to_markdown(all_results, out_path)
    else:
        export.to_table(all_results)
        export.to_markdown(all_results, out_path)


@app.command()
def platforms():
    """List supported platforms and their status."""
    console.print("[bold]Supported platforms:[/bold]")
    console.print("  [green]linkedin[/green]      — LinkedIn guest API (no auth required, works globally)")
    console.print("  [green]francetravail[/green] — France Travail website (FR only, no auth required)")
    console.print("  [green]remoteok[/green]      — RemoteOK public API (100% remote, global)")
