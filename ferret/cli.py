import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich import box
from typing import Optional, List
from datetime import datetime

from ferret.report import Report, TraceNode, AggregatedStats

app = typer.Typer(help="Ferret Performance Analyzer")
console = Console()

def get_latest_run_id(report: Report) -> str | None:
    """
    Scans the log to find the most recent Run ID.
    Note: In a massive DB, this should be optimized with a separate index/table.
    """
    # Fetch recent entries to find the last run_id
    # We rely on the log being append-only and time-sorted.
    # Reading from the end (conceptually) - here we just fetch all for MVP simplicity
    entries = [d[1] for d in report.log_manager]

    if not entries:
        return None

    # Return the run_id of the very last entry
    return entries[-1].run_id

def print_table(stats: List[AggregatedStats], limit: int):
    table = Table(title="Performance Summary", box=box.SIMPLE, show_header=True)

    table.add_column("Function Name", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right")
    table.add_column("Total Time", justify="right")
    table.add_column("Avg Time", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Error %", justify="right", style="red")

    # Sort by total duration descending
    stats.sort(key=lambda s: s.total_duration, reverse=True)

    for stat in stats[:limit]:
        table.add_row(
            stat.name,
            str(stat.count),
            f"{stat.total_duration:.3f}s",
            f"{stat.avg_duration * 1000:.2f}ms",
            f"{stat.min_duration * 1000:.2f}ms",
            f"{stat.max_duration * 1000:.2f}ms",
            f"{stat.error_rate * 100:.1f}%"
        )

    console.print(table)

def build_rich_tree(node: TraceNode, tree: Tree):
    """Recursively adds nodes to a Rich Tree."""
    duration_ms = (node.span.duration or 0) * 1000

    # Color code duration
    if duration_ms > 100:
        time_style = "red"
    elif duration_ms > 50:
        time_style = "yellow"
    else:
        time_style = "green"

    label = f"[bold cyan]{node.span.name}[/] - [{time_style}]{duration_ms:.2f}ms[/{time_style}]"

    if node.span.tags:
        tags_str = ", ".join(f"{k}={v}" for k, v in node.span.tags.items())
        label += f" [dim]({tags_str})[/dim]"

    if node.span.status != "ok":
        label += " [bold red]![/]"

    branch = tree.add(label)

    for child in node.children:
        build_rich_tree(child, branch)

@app.command()
def main(
    db_path: str = typer.Argument(..., help="Path to the BeaverDB file"),
    tree: bool = typer.Option(False, "--tree", "-t", help="Show hierarchical tree view instead of table"),
    run_id: Optional[str] = typer.Option(None, "--run", "-r", help="Filter by specific Run ID. Defaults to latest."),
    limit: int = typer.Option(20, "--limit", "-l", help="Limit output rows/trees"),
):
    """
    Analyze Ferret performance traces.
    """
    try:
        report = Report(db_path)
    except Exception as e:
        console.print(f"[bold red]Error opening DB:[/bold red] {e}")
        raise typer.Exit(code=1)

    # 1. Determine Run ID
    target_run = run_id
    if not target_run:
        with console.status("Finding latest run..."):
            target_run = get_latest_run_id(report)

    if not target_run:
        console.print("[yellow]No traces found in database.[/yellow]")
        raise typer.Exit()

    console.print(f"Analyzing Run ID: [bold green]{target_run}[/bold green]")

    # 2. Render View
    if tree:
        with console.status("Building trees..."):
            roots = report.build_trees(target_run)

        # Sort by duration slowest first
        roots.sort(key=lambda n: n.span.duration or 0, reverse=True)

        console.print(f"\n[bold]Top {limit} Slowest Traces[/bold]")
        for root in roots[:limit]:
            root_tree = Tree("Trace Root", hide_root=True)
            build_rich_tree(root, root_tree)
            console.print(root_tree)
            console.print("") # spacing

    else:
        with console.status("Computing aggregates..."):
            stats_dict = report.analyze_run(target_run)
            stats_list = list(stats_dict.values())

        print_table(stats_list, limit)

    report.close()

if __name__ == "__main__":
    app()