import typer
import sys
import os
import ast
import builtins
import importlib.util
from importlib.abc import MetaPathFinder
from importlib.machinery import SourceFileLoader, FileFinder
from importlib.util import decode_source
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich import box
from typing import Optional, List
from datetime import datetime

from ferret.report import Report, TraceNode, AggregatedStats
from ferret.core import Profiler

app = typer.Typer(help="Ferret Performance Analyzer")
console = Console()

# --- Instrumentation Logic ---

class FerretInstrumentor(ast.NodeTransformer):
    """
    AST Transformer that automagically injects the @_ferret_profiler.measure decorator
    into every synchronous and asynchronous function definition.
    """
    def visit_FunctionDef(self, node):
        return self._inject_decorator(node)

    def visit_AsyncFunctionDef(self, node):
        return self._inject_decorator(node)

    def _inject_decorator(self, node):
        # Create the AST node for: @_ferret_profiler.measure("function_name")
        # We assume '_ferret_profiler' is available in builtins.
        decorator = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='_ferret_profiler', ctx=ast.Load()),
                attr='measure',
                ctx=ast.Load()
            ),
            args=[ast.Constant(value=node.name)],
            keywords=[]
        )

        # Insert as the first decorator
        node.decorator_list.insert(0, decorator)
        return self.generic_visit(node)

class FerretSourceFileLoader(SourceFileLoader):
    """
    Custom Loader that instruments code on-the-fly during import.
    """
    def get_code(self, fullname):
        filename = self.get_filename(fullname)

        # Simple heuristic: Only instrument user code (inside current working directory)
        # preventing instrumentation of system libraries or venv files.
        if os.getcwd() in os.path.abspath(filename):
            try:
                # Read original source
                data = self.get_data(filename)
                source = decode_source(data)

                # Parse -> Instrument -> Compile
                tree = ast.parse(source, filename)
                tree = FerretInstrumentor().visit(tree)
                ast.fix_missing_locations(tree)
                return compile(tree, filename, 'exec')
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to instrument {filename}: {e}[/yellow]")

        # Fallback to standard loading for libraries/external files
        return super().get_code(fullname)

def install_import_hook():
    """
    Installs the Ferret loader into sys.path_hooks to intercept imports.
    """
    loader_details = (FerretSourceFileLoader, SourceFileLoader.SOURCE_SUFFIXES)

    def hook(path):
        # Only hook into paths inside the project directory
        if os.getcwd() not in os.path.abspath(path):
             raise ImportError
        return FileFinder(path, loader_details)

    sys.path_hooks.insert(0, hook)
    # Clear cache to ensure our hook is used for subsequent imports
    sys.path_importer_cache.clear()

# --- CLI Commands ---

@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def run(
    ctx: typer.Context,
    script: str = typer.Argument(..., help="Path to the Python script to run"),
    db_path: str = typer.Option("ferret.db", "--db", help="Path to store the trace database"),
):
    """
    Run a Python script with automatic Ferret instrumentation.
    This injects decorators into functions in the script and local imports.
    """
    # 1. Initialize Profiler
    profiler = Profiler(db_path, run_id=None) # Generates a new UUID

    # Inject into builtins so the AST-injected code can find it without imports
    builtins._ferret_profiler = profiler

    # 2. Install Import Hook (handles imports within the script)
    install_import_hook()

    # 3. Setup Environment (mimic real execution)
    sys.argv = [script] + ctx.args
    # Add script directory to path so imports work as expected
    script_dir = os.path.dirname(os.path.abspath(script))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    console.print(f"[bold green]Ferreting[/bold green] {script} (Run ID: {profiler.run_id})...")

    # 4. Instrument and Execute Main Script
    try:
        with open(script, "rb") as f:
            source = decode_source(f.read())

        # Instrument entry point manually
        tree = ast.parse(source, script)
        tree = FerretInstrumentor().visit(tree)
        ast.fix_missing_locations(tree)
        code = compile(tree, script, "exec")

        # Execute
        globs = {
            "__name__": "__main__",
            "__file__": script,
            "__doc__": None,
        }
        exec(code, globs)

    except Exception as e:
        console.print(f"[bold red]Script Failed:[/bold red] {e}")
        # Depending on preference, might want to re-raise or just exit
    finally:
        profiler.close()
        console.print(f"Trace saved to [bold]{db_path}[/bold]")

# --- Existing Analysis Commands ---

def get_latest_run_id(report: Report) -> str | None:
    entries = [d[1] for d in report.log_manager]
    if not entries:
        return None
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
    duration_ms = (node.span.duration or 0) * 1000
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
def analyze(
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

    target_run = run_id
    if not target_run:
        with console.status("Finding latest run..."):
            target_run = get_latest_run_id(report)

    if not target_run:
        console.print("[yellow]No traces found in database.[/yellow]")
        raise typer.Exit()

    console.print(f"Analyzing Run ID: [bold green]{target_run}[/bold green]")

    if tree:
        with console.status("Building trees..."):
            roots = report.build_trees(target_run)
        roots.sort(key=lambda n: n.span.duration or 0, reverse=True)
        console.print(f"\n[bold]Top {limit} Slowest Traces[/bold]")
        for root in roots[:limit]:
            root_tree = Tree("Trace Root", hide_root=True)
            build_rich_tree(root, root_tree)
            console.print(root_tree)
            console.print("")
    else:
        with console.status("Computing aggregates..."):
            stats_dict = report.analyze_run(target_run)
            stats_list = list(stats_dict.values())
        print_table(stats_list, limit)
    report.close()

if __name__ == "__main__":
    app()