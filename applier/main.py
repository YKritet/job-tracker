import os
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional
from dotenv import load_dotenv
import typer
from rich.console import Console
from rich.table import Table

from .search.linkedin import LinkedInSearcher
from .search.francetravail import FranceTravailSearcher
from .search.remoteok import RemoteOKSearcher
from .search.indeed_fr import IndeedFRSearcher
from .search.wttj import WTTJSearcher
from .search.hellowork import HelloWorkSearcher
from .search.apec import APECSearcher
from .search.keljob import KeljobSearcher
from .search.aeroemploi import AeroEmploiSearcher
from .search.adecco import AdeccoSearcher
from .search.manpower import ManpowerSearcher
from .search.randstad import RandstadSearcher
from .search.synergie import SynergieSearcher
from .search.hays import HaysSearcher
from .search.michaelpage import MichaelPageSearcher
from .search.malt import MaltSearcher
from .search.jobetudiant import JobEtudiantSearcher
from .search.side import SideSearcher
from .search.cadremploi import CadrEmploiSearcher
from .search.meteojob import MeteojobSearcher
from .search.jobijoba import JobijobaSearcher
from .search.monster_fr import MonsterFRSearcher
from .search.optioncarriere import OptionCarriereSearcher
from .search.staffme import StaffmeSearcher
from .search.base import JobResult, auto_tag, detect_poste, detect_domain, detect_skills
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


def _make_exclude_check(exclude_kws: tuple[str, ...]):
    """Return a closure that returns True when a job should be excluded."""
    if not exclude_kws:
        return lambda _: False

    def _check(r: JobResult) -> bool:
        text = (r.title + " " + r.contract).lower()
        return any(kw in text for kw in exclude_kws)

    return _check


@app.command()
def search(
    profile: Annotated[Path, typer.Option("--profile", "-p")] = Path("profiles/hamza.toml"),
    platforms: Annotated[str, typer.Option(help="Comma-separated: linkedin,francetravail,indeed_fr,wttj,hellowork,apec,keljob,aeroemploi,adecco,manpower,randstad,synergie,hays,michaelpage,malt,jobetudiant,side,cadremploi,meteojob,jobijoba,monster_fr,optioncarriere,staffme,remoteok")] = "linkedin,francetravail,indeed_fr,wttj,hellowork,keljob,meteojob,jobijoba,monster_fr,optioncarriere",
    locations: Annotated[str, typer.Option(help="Location labels from profile, or 'all'")] = "all",
    count: Annotated[int, typer.Option(help="Max results per query")] = 25,
    output: Annotated[str, typer.Option(help="Output file (.html/.xlsx/.csv/.json)")] = "results/jobs.html",
    fmt: Annotated[str, typer.Option("--format", help="Force format: html, xlsx, csv, json")] = "",
    no_filter: Annotated[bool, typer.Option("--no-filter", help="Disable alternance + exclusion filtering")] = False,
):
    """Search for jobs across platforms and export to the tracker."""

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

    # Load profile-level exclusion keywords
    filter_cfg = cfg.get("filter", {})
    exclude_kws = tuple(kw.lower() for kw in filter_cfg.get("exclude_keywords", []))
    _is_excluded = _make_exclude_check(exclude_kws)

    active_platforms = {p.strip().lower() for p in platforms.split(",")}
    fr_roles = search_cfg.get("roles_fr", [])
    en_roles = search_cfg.get("roles_en", [])
    li_at = os.getenv("LINKEDIN_LI_AT", "")
    pulled_at = datetime.now().strftime("%Y-%m-%d")

    all_results: list[JobResult] = []
    seen_urls: set[str] = set()
    skipped_alt = 0
    skipped_excl = 0

    def add_results(new: list[JobResult], label: str) -> None:
        nonlocal skipped_alt, skipped_excl
        added = 0
        for r in new:
            if r.url in seen_urls:
                continue
            if not no_filter and _is_alternance(r):
                skipped_alt += 1
                continue
            if not no_filter and _is_excluded(r):
                skipped_excl += 1
                continue
            r.pulled_at = pulled_at
            r.tags  = auto_tag(r.title, r.location, r.contract)
            r.poste  = detect_poste(r.title)
            r.domain = detect_domain(r.title, r.company)
            r.skills = detect_skills(r.title)
            seen_urls.add(r.url)
            all_results.append(r)
            added += 1
        console.print(f"    +{added} ({label})")

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
                    db.log_source_check(f"linkedin/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]LinkedIn:[/red] {e}")
                    db.log_source_check(f"linkedin/{label}/{role[:30]}", 0, "error")

            if "francetravail" in active_platforms and country == "FR":
                try:
                    raw = FranceTravailSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"FranceTravail · {role[:40]}")
                    db.log_source_check(f"francetravail/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]FranceTravail:[/red] {e}")
                    db.log_source_check(f"francetravail/{label}/{role[:30]}", 0, "error")

            if "indeed_fr" in active_platforms and country == "FR":
                try:
                    raw = IndeedFRSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Indeed · {role[:40]}")
                    db.log_source_check(f"indeed/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Indeed FR:[/red] {e}")
                    db.log_source_check(f"indeed/{label}/{role[:30]}", 0, "error")

            if "wttj" in active_platforms:
                try:
                    raw = WTTJSearcher().search(role, label, count)
                    add_results(raw, f"WTTJ · {role[:40]}")
                    db.log_source_check(f"wttj/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]WTTJ:[/red] {e}")
                    db.log_source_check(f"wttj/{label}/{role[:30]}", 0, "error")

            if "hellowork" in active_platforms and country == "FR":
                try:
                    raw = HelloWorkSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"HelloWork · {role[:40]}")
                    db.log_source_check(f"hellowork/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]HelloWork:[/red] {e}")
                    db.log_source_check(f"hellowork/{label}/{role[:30]}", 0, "error")

            if "apec" in active_platforms and country == "FR":
                try:
                    raw = APECSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"APEC · {role[:40]}")
                    db.log_source_check(f"apec/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]APEC:[/red] {e}")
                    db.log_source_check(f"apec/{label}/{role[:30]}", 0, "error")

            if "keljob" in active_platforms and country == "FR":
                try:
                    raw = KeljobSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Keljob · {role[:40]}")
                    db.log_source_check(f"keljob/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Keljob:[/red] {e}")
                    db.log_source_check(f"keljob/{label}/{role[:30]}", 0, "error")

            if "aeroemploi" in active_platforms and country == "FR":
                try:
                    raw = AeroEmploiSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"AeroEmploi · {role[:40]}")
                    db.log_source_check(f"aeroemploi/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]AeroEmploi:[/red] {e}")
                    db.log_source_check(f"aeroemploi/{label}/{role[:30]}", 0, "error")

            if "adecco" in active_platforms and country == "FR":
                try:
                    raw = AdeccoSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Adecco · {role[:40]}")
                    db.log_source_check(f"adecco/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Adecco:[/red] {e}")
                    db.log_source_check(f"adecco/{label}/{role[:30]}", 0, "error")

            if "manpower" in active_platforms and country == "FR":
                try:
                    raw = ManpowerSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Manpower · {role[:40]}")
                    db.log_source_check(f"manpower/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Manpower:[/red] {e}")
                    db.log_source_check(f"manpower/{label}/{role[:30]}", 0, "error")

            if "randstad" in active_platforms and country == "FR":
                try:
                    raw = RandstadSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Randstad · {role[:40]}")
                    db.log_source_check(f"randstad/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Randstad:[/red] {e}")
                    db.log_source_check(f"randstad/{label}/{role[:30]}", 0, "error")

            if "synergie" in active_platforms and country == "FR":
                try:
                    raw = SynergieSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Synergie · {role[:40]}")
                    db.log_source_check(f"synergie/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Synergie:[/red] {e}")
                    db.log_source_check(f"synergie/{label}/{role[:30]}", 0, "error")

            if "hays" in active_platforms and country == "FR":
                try:
                    raw = HaysSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Hays · {role[:40]}")
                    db.log_source_check(f"hays/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Hays:[/red] {e}")
                    db.log_source_check(f"hays/{label}/{role[:30]}", 0, "error")

            if "michaelpage" in active_platforms and country == "FR":
                try:
                    raw = MichaelPageSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Michael Page · {role[:40]}")
                    db.log_source_check(f"michaelpage/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Michael Page:[/red] {e}")
                    db.log_source_check(f"michaelpage/{label}/{role[:30]}", 0, "error")

            if "malt" in active_platforms and country == "FR":
                try:
                    raw = MaltSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Malt · {role[:40]}")
                    db.log_source_check(f"malt/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Malt:[/red] {e}")
                    db.log_source_check(f"malt/{label}/{role[:30]}", 0, "error")

            if "jobetudiant" in active_platforms and country == "FR":
                try:
                    raw = JobEtudiantSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"JobEtudiant · {role[:40]}")
                    db.log_source_check(f"jobetudiant/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]JobEtudiant:[/red] {e}")
                    db.log_source_check(f"jobetudiant/{label}/{role[:30]}", 0, "error")

            if "side" in active_platforms and country == "FR":
                try:
                    raw = SideSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Side · {role[:40]}")
                    db.log_source_check(f"side/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Side:[/red] {e}")
                    db.log_source_check(f"side/{label}/{role[:30]}", 0, "error")

            if "cadremploi" in active_platforms and country == "FR":
                try:
                    raw = CadrEmploiSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Cadremploi · {role[:40]}")
                    db.log_source_check(f"cadremploi/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Cadremploi:[/red] {e}")
                    db.log_source_check(f"cadremploi/{label}/{role[:30]}", 0, "error")

            if "meteojob" in active_platforms and country == "FR":
                try:
                    raw = MeteojobSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Meteojob · {role[:40]}")
                    db.log_source_check(f"meteojob/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Meteojob:[/red] {e}")
                    db.log_source_check(f"meteojob/{label}/{role[:30]}", 0, "error")

            if "jobijoba" in active_platforms and country == "FR":
                try:
                    raw = JobijobaSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Jobijoba · {role[:40]}")
                    db.log_source_check(f"jobijoba/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Jobijoba:[/red] {e}")
                    db.log_source_check(f"jobijoba/{label}/{role[:30]}", 0, "error")

            if "monster_fr" in active_platforms and country == "FR":
                try:
                    raw = MonsterFRSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Monster · {role[:40]}")
                    db.log_source_check(f"monster_fr/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Monster FR:[/red] {e}")
                    db.log_source_check(f"monster_fr/{label}/{role[:30]}", 0, "error")

            if "optioncarriere" in active_platforms and country == "FR":
                try:
                    raw = OptionCarriereSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"OptionCarriere · {role[:40]}")
                    db.log_source_check(f"optioncarriere/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]OptionCarriere:[/red] {e}")
                    db.log_source_check(f"optioncarriere/{label}/{role[:30]}", 0, "error")

            if "staffme" in active_platforms and country == "FR":
                try:
                    raw = StaffmeSearcher().search(role, ft_location or label, count)
                    add_results(raw, f"Staffme · {role[:40]}")
                    db.log_source_check(f"staffme/{label}/{role[:30]}", len(raw))
                except Exception as e:
                    console.print(f"  [red]Staffme:[/red] {e}")
                    db.log_source_check(f"staffme/{label}/{role[:30]}", 0, "error")

    if "remoteok" in active_platforms:
        console.print(f"\n[cyan]── Remote (global)[/cyan]")
        for tag in ["sales", "marketing", "it", "business-development", "technical-account-manager"]:
            try:
                raw = RemoteOKSearcher().search(tag, "remote", count)
                add_results(raw, f"RemoteOK · {tag}")
                db.log_source_check(f"remoteok/{tag}", len(raw))
            except Exception as e:
                console.print(f"  [red]RemoteOK:[/red] {e}")
                db.log_source_check(f"remoteok/{tag}", 0, "error")

    console.print(f"\n[bold green]{len(all_results)} jobs found[/bold green]", end="")
    skipped_parts = []
    if skipped_alt:
        skipped_parts.append(f"{skipped_alt} alternance")
    if skipped_excl:
        skipped_parts.append(f"{skipped_excl} excluded by profile")
    if skipped_parts:
        console.print(f" [dim]({', '.join(skipped_parts)} filtered out)[/dim]")
    else:
        console.print()

    if not all_results:
        console.print("[yellow]No results.[/yellow]")
        raise typer.Exit(0)

    # Always persist to DB
    db.init_db()
    db.upsert_jobs(all_results)
    console.print(f"[dim]  → saved to DB ({db._DB_PATH})[/dim]")

    # Always purge jobs older than 30 days
    deleted = db.purge_old_jobs(30)
    if deleted:
        console.print(f"[dim]  → purged {deleted} job(s) older than 30 days[/dim]")

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


@app.command("parse-cv")
def parse_cv(
    cv: Annotated[Path, typer.Option("--cv", help="Path to CV PDF")] = Path("assets/cv.pdf"),
    letter: Annotated[Optional[Path], typer.Option("--letter", help="Path to motivation letter PDF")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("profiles/auto.toml"),
    name: Annotated[str, typer.Option("--name", help="Override detected candidate name")] = "",
):
    """Parse a CV PDF (and optionally a motivation letter) to auto-generate a search profile."""
    from . import parse as cv_parser

    if not cv.exists():
        console.print(f"[red]CV not found: {cv}[/red]")
        console.print("[dim]Drop your CV at assets/cv.pdf or pass --cv path/to/cv.pdf[/dim]")
        raise typer.Exit(1)

    console.print(f"[cyan]Parsing:[/cyan] {cv}")
    if letter and letter.exists():
        console.print(f"[cyan]Parsing:[/cyan] {letter}")
    elif letter:
        console.print(f"[yellow]Letter not found ({letter}), skipping[/yellow]")

    result = cv_parser.generate_profile(cv, letter, output, name)

    console.print(f"\n[bold green]Profile written:[/bold green] {output}")
    console.print(f"  Name:       {result['name'] or '[dim](not detected — edit profile)[/dim]'}")
    console.print(f"  Email:      {result['email'] or '[dim](not detected)[/dim]'}")
    if result["categories"]:
        console.print(f"  Detected:   {', '.join(result['categories'])}")
    else:
        console.print("  [yellow]No categories detected — add roles manually in the profile[/yellow]")
    console.print(f"  FR queries: {result['roles_fr_count']}")
    console.print(f"  EN queries: {result['roles_en_count']}")
    console.print(f"\n[dim]Review {output}, then run:[/dim]")
    console.print(f"  applier search --profile {output}")


@app.command()
def platforms():
    """List supported platforms."""
    console.print("  [green]linkedin[/green]      — LinkedIn guest API (no auth)              [Tier 1]")
    console.print("  [green]francetravail[/green] — France Travail API (FR only)               [Tier 1]")
    console.print("  [green]indeed_fr[/green]     — Indeed France RSS feed                     [Tier 1]")
    console.print("  [green]wttj[/green]          — Welcome to the Jungle public API           [Tier 1]")
    console.print("  [green]remoteok[/green]      — RemoteOK public API (remote, global)       [Tier 1]")
    console.print("  [green]hellowork[/green]     — HelloWork HTML scraper (FR)                [Tier 2]")
    console.print("  [green]apec[/green]          — APEC HTML scraper (FR, cadres)             [Tier 2]")
    console.print("  [green]keljob[/green]        — Keljob HTML scraper (FR)                   [Tier 2]")
    console.print("  [green]aeroemploi[/green]    — AeroEmploi HTML scraper (FR, aéroport)     [Tier 2]")
    console.print("  [green]adecco[/green]        — Adecco HTML scraper (FR, intérim)          [Tier 2]")
    console.print("  [green]manpower[/green]      — Manpower HTML scraper (FR, intérim)        [Tier 2]")
    console.print("  [green]randstad[/green]      — Randstad HTML scraper (FR, intérim)        [Tier 2]")
    console.print("  [green]synergie[/green]      — Synergie HTML scraper (FR, intérim)        [Tier 2]")
    console.print("  [green]hays[/green]          — Hays HTML scraper (FR, cadres/intérim)     [Tier 2]")
    console.print("  [green]michaelpage[/green]   — Michael Page HTML scraper (FR, cadres)     [Tier 2]")
    console.print("  [green]cadremploi[/green]    — Cadremploi HTML scraper (FR, cadres)       [Tier 2]")
    console.print("  [green]malt[/green]          — Malt HTML scraper (FR, freelance)          [Tier 2]")
    console.print("  [green]jobetudiant[/green]   — JobEtudiant HTML scraper (FR, étudiant)    [Tier 2]")
    console.print("  [green]side[/green]          — Side HTML scraper (FR, étudiant/intérim)   [Tier 2]")
    console.print("  [green]meteojob[/green]      — Meteojob HTML scraper (FR, tous secteurs)  [Tier 2]")
    console.print("  [green]jobijoba[/green]      — Jobijoba HTML scraper (FR, agrégateur)     [Tier 2]")
    console.print("  [green]monster_fr[/green]    — Monster France HTML scraper                [Tier 2]")
    console.print("  [green]optioncarriere[/green]— OptionCarriere HTML scraper (FR)           [Tier 2]")
    console.print("  [green]staffme[/green]       — Staffme Playwright scraper (FR, missions)  [Tier 3]")


@app.command()
def purge(
    days: Annotated[int, typer.Option("--days", help="Delete jobs older than N days")] = 30,
):
    """Delete stale jobs from the DB (default: older than 30 days)."""
    db.init_db()
    deleted = db.purge_old_jobs(days)
    console.print(f"[green]Deleted {deleted} job(s) older than {days} days.[/green]")


@app.command("watchlist-check")
def watchlist_check(
    watchlist: Annotated[Path, typer.Option("--watchlist", "-w", help="Path to companies.toml")] = Path("watchlist/companies.toml"),
    timeout: Annotated[int, typer.Option(help="HTTP timeout per request (seconds)")] = 10,
    sector: Annotated[str, typer.Option(help="Filter by sector (e.g. logistique, transport)")] = "",
):
    """Fetch company career pages, detect content changes, and log results to DB."""
    import hashlib
    import httpx

    if not watchlist.exists():
        console.print(f"[red]Watchlist not found: {watchlist}[/red]")
        raise typer.Exit(1)

    with watchlist.open("rb") as f:
        wl = tomllib.load(f)

    companies = wl.get("company", [])
    if sector:
        companies = [c for c in companies if c.get("sector", "").lower() == sector.lower()]

    if not companies:
        console.print("[yellow]No companies to check.[/yellow]")
        return

    db.init_db()

    table = Table(
        title=f"Career Page Check ({len(companies)} companies)",
        show_lines=False,
        expand=True,
    )
    table.add_column("Company", style="cyan", no_wrap=True)
    table.add_column("Sector", style="dim")
    table.add_column("HTTP", justify="center")
    table.add_column("Change", justify="center")

    changed: list[dict] = []
    ua = {"User-Agent": "Mozilla/5.0 (compatible; ApplierBot/1.0)"}

    with httpx.Client(timeout=timeout, follow_redirects=True, headers=ua) as client:
        for c in companies:
            name = c["name"]
            url = c["careers_url"]
            sec = c.get("sector", "")
            try:
                resp = client.get(url)
                resp.raise_for_status()
                h = hashlib.sha256(resp.text.encode()).hexdigest()[:16]
                prev = db.get_watchlist_snap(name)
                is_new = prev is None
                changed_flag = prev is not None and prev["content_hash"] != h
                db.set_watchlist_snap(name, url, h, "ok")
                db.log_source_check(f"watchlist/{name}", 0, "ok")

                http_str = "[green]OK[/green]"
                if is_new:
                    change_str = "[dim]baseline[/dim]"
                elif changed_flag:
                    change_str = "[bold yellow]CHANGED[/bold yellow]"
                    changed.append(c)
                else:
                    change_str = "[dim]same[/dim]"
            except httpx.HTTPStatusError as e:
                db.set_watchlist_snap(name, url, "", "error")
                db.log_source_check(f"watchlist/{name}", 0, "error")
                http_str = f"[red]{e.response.status_code}[/red]"
                change_str = "[dim]—[/dim]"
            except Exception as e:
                db.set_watchlist_snap(name, url, "", "error")
                db.log_source_check(f"watchlist/{name}", 0, "error")
                http_str = "[red]ERR[/red]"
                change_str = f"[dim]{str(e)[:30]}[/dim]"

            table.add_row(name, sec, http_str, change_str)

    console.print(table)

    if changed:
        console.print(f"\n[bold yellow]{len(changed)} career page(s) changed:[/bold yellow]")
        for c in changed:
            console.print(f"  [yellow]→[/yellow] {c['name']} — {c['careers_url']}")
    else:
        console.print(f"\n[dim]No changes across {len(companies)} career pages.[/dim]")


@app.command()
def coverage(
    days: Annotated[int, typer.Option(help="Show sources not checked in the last N days")] = 7,
):
    """Show which sources were checked and when — flag stale or unchecked sources."""
    db.init_db()
    rows = db.get_coverage()
    if not rows:
        console.print("[yellow]No source checks recorded yet. Run 'applier search' first.[/yellow]")
        return

    table = Table(title=f"Source Coverage (last {days} days)", show_lines=False, expand=True)
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("Last checked", style="dim")
    table.add_column("Jobs found", justify="right")
    table.add_column("Checks", justify="right")
    table.add_column("Status", justify="center")

    from datetime import datetime, timedelta
    stale_cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    for row in rows:
        last = row["last_checked"] or "never"
        is_stale = not row["last_checked"] or row["last_checked"][:10] < stale_cutoff
        status_str = (
            "[red]STALE[/red]" if is_stale else
            "[red]ERROR[/red]" if row["last_status"] == "error" else
            "[green]OK[/green]"
        )
        table.add_row(
            row["source"],
            last[:16] if last != "never" else "[red]never[/red]",
            str(row["total_found"] or 0),
            str(row["checks"] or 0),
            status_str,
        )

    console.print(table)
