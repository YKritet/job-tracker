import csv
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from .search.base import JobResult

console = Console()


def to_table(results: list[JobResult]) -> None:
    table = Table(title=f"Jobs found: {len(results)}", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Platform", style="cyan")
    table.add_column("Contract", style="green")

    for i, r in enumerate(results, 1):
        table.add_row(str(i), r.title, r.company, r.location, r.platform, r.contract)

    console.print(table)


def to_markdown(results: list[JobResult], path: Path) -> None:
    lines = [
        f"# Job Results — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"\n{len(results)} listings found.\n",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **[{r.title}]({r.url})** — {r.company} | {r.location} | {r.platform} | {r.contract}")
    path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]Saved {len(results)} results → {path}[/green]")


def to_csv(results: list[JobResult], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title", "company", "location", "url", "platform", "contract"])
        w.writeheader()
        for r in results:
            w.writerow({"title": r.title, "company": r.company, "location": r.location,
                        "url": r.url, "platform": r.platform, "contract": r.contract})
    console.print(f"[green]Saved {len(results)} results → {path}[/green]")


def to_json(results: list[JobResult], path: Path) -> None:
    data = [{"title": r.title, "company": r.company, "location": r.location,
             "url": r.url, "platform": r.platform, "contract": r.contract}
            for r in results]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]Saved {len(results)} results → {path}[/green]")
