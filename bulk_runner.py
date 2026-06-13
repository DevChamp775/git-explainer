# type: ignore
"""
BULK RUNNER — Continuous Learning Pipeline
==========================================
Feed multiple GitHub repos → system explains each file
→ saves to RAG memory → saves to dataset
→ each new repo benefits from all previous repos' context
→ model gets smarter with every run

Run:  python bulk_runner.py
"""

import os
import time
import shutil
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

console = Console(force_terminal=True)

# =====================================================
# ADD YOUR REPOS HERE
# =====================================================

REPOS = [
    # Python
    "https://github.com/pallets/flask",
    "https://github.com/psf/requests",
    "https://github.com/fastapi/fastapi",
    "https://github.com/django/django",
    "https://github.com/numpy/numpy",
    "https://github.com/keras-team/keras",
    "https://github.com/scikit-learn/scikit-learn",
    "https://github.com/sqlalchemy/sqlalchemy",
    # JavaScript
    "https://github.com/expressjs/express",
    "https://github.com/axios/axios",
    "https://github.com/lodash/lodash",
    "https://github.com/moment/moment",
    # Add your own below:
    # "https://github.com/owner/repo",
]

# =====================================================
# CONFIGURATION
# =====================================================

MAX_FILES_PER_REPO = 10     # files to explain per repo
CODE_LIMIT         = 8000   # chars per file
DELAY_BETWEEN      = 3      # seconds between repos (avoid rate limits)
LOG_FILE           = "bulk_run_log.jsonl"


# =====================================================
# IMPORTS
# =====================================================

from clone_repo import clone_repo, fetch_repository_info
from file_extractor import get_code_files, get_important_files
from reader import read_file
from ai_explainer import explain_file, summarize_repo
from my_utils import short_path
from dataset_saver import get_count, save_example
from rag_memory import get_memory_size


# =====================================================
# LOGGING
# =====================================================

def log_result(repo_url, status, files_processed, elapsed, error=""):
    entry = {
        "repo":            repo_url,
        "status":          status,
        "files_processed": files_processed,
        "elapsed_seconds": round(elapsed, 1),
        "error":           error,
        "timestamp":       datetime.now().isoformat(),
        "rag_size_after":  get_memory_size(),
        "dataset_after":   get_count()
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_completed_repos():
    """Returns set of repo URLs already processed successfully."""
    completed = set()
    if not os.path.exists(LOG_FILE):
        return completed
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("status") == "done":
                    completed.add(entry["repo"])
            except Exception:
                continue
    return completed


# =====================================================
# PROCESS A SINGLE REPO
# =====================================================

def process_single_repo(repo_url, repo_num, total_repos):
    """
    Full pipeline for one repo:
    fetch → clone → extract → explain → save to RAG + dataset
    Returns number of files processed.
    """
    start = time.time()
    repo_name = repo_url.rstrip("/").split("/")[-1]

    console.print(f"\n[bold blue]({repo_num}/{total_repos})[/] [white]{repo_url}[/]")

    # ── Fetch repo info ──
    repo_info = fetch_repository_info(repo_url)
    if not repo_info:
        console.print(f"  [red]✗ Could not fetch repo info[/]")
        return 0

    console.print(
        f"  [dim]⭐ {repo_info.get('stargazers_count',0):,}  "
        f"· {repo_info.get('language','?')}  "
        f"· {repo_info.get('forks_count',0):,} forks[/]"
    )

    # ── Clone ──
    console.print(f"  [dim]Cloning...[/]", end=" ")
    repo_path = clone_repo(repo_url)
    if not repo_path:
        console.print(f"[red]✗ Clone failed[/]")
        return 0
    console.print(f"[green]✔[/]")

    files_processed = 0

    try:
        # ── Extract files ──
        all_files = get_code_files(repo_path)
        if not all_files:
            console.print(f"  [dim]No source files found[/]")
            return 0

        selected = get_important_files(all_files, MAX_FILES_PER_REPO)
        console.print(
            f"  [dim]Files: {len(all_files)} found "
            f"· {len(selected)} selected[/]"
        )

        # ── Generate summary ──
        combined = ""
        for f in selected:
            code = read_file(f)
            if code.strip():
                combined += f"\n\n### {short_path(f)}\n{code[:2000]}\n"

        if combined.strip():
            console.print(f"  [dim]Generating summary...[/]", end=" ")
            summary = summarize_repo(combined)
            # Save summary as a dataset example too
            save_example(
                combined[:8000],
                summary,
                file_path="__summary__",
                repo_url=repo_url
            )
            console.print(f"[green]✔[/]")

        # ── Explain each file ──
        for idx, f in enumerate(selected, 1):
            code = read_file(f)
            if not code.strip():
                continue

            fname = short_path(f)
            console.print(
                f"  [dim]({idx}/{len(selected)}) {fname}...[/]",
                end=" "
            )

            explanation = explain_file(
                code[:CODE_LIMIT],
                file_path=f,
                repo_url=repo_url
            )

            if explanation and not explanation.startswith("[ERROR]"):
                files_processed += 1
                console.print(f"[green]✔[/]")
            else:
                console.print(f"[red]✗ {explanation[:50]}[/]")

    finally:
        shutil.rmtree(repo_path, ignore_errors=True)

    elapsed = time.time() - start
    log_result(repo_url, "done", files_processed, elapsed)

    console.print(
        f"  [bold green]✔ Done[/] "
        f"[dim]· {files_processed} files "
        f"· {elapsed:.0f}s "
        f"· RAG: {get_memory_size()} "
        f"· Dataset: {get_count()}[/]"
    )

    return files_processed


# =====================================================
# SHOW PROGRESS STATS
# =====================================================

def show_stats(processed_count, failed_count, total_files, elapsed):
    table = Table(
        box=box.ROUNDED,
        show_header=False,
        border_style="magenta",
        padding=(0, 2)
    )
    table.add_column("Key",   style="dim cyan", width=22)
    table.add_column("Value", style="bold white")

    rag     = get_memory_size()
    dataset = get_count()
    ready   = "✅ Yes!" if dataset >= 500 else f"Need {500 - dataset} more"

    table.add_row("Repos processed",   f"[green]{processed_count}[/]")
    table.add_row("Repos failed",      f"[red]{failed_count}[/]")
    table.add_row("Total files",       f"[yellow]{total_files}[/]")
    table.add_row("Time elapsed",      f"{elapsed:.0f}s")
    table.add_row("RAG memory",        f"[cyan]{rag}[/] entries")
    table.add_row("Dataset size",      f"[yellow]{dataset}[/] examples")
    table.add_row("Fine-tune ready",   ready)

    console.print(Panel(
        table,
        title="[bold magenta]📦 Bulk Run Complete[/]",
        border_style="magenta",
        padding=(1, 1)
    ))


# =====================================================
# MAIN BULK RUNNER
# =====================================================

def run_bulk(repos=None, skip_completed=True):
    """
    Run the full pipeline on multiple repos.
    skip_completed=True skips repos already in the log.
    """
    if repos is None:
        repos = REPOS

    console.print()
    console.print(Panel.fit(
        "[bold magenta]Bulk Runner — Continuous Learning Pipeline[/]\n"
        "[dim]Each repo makes the AI smarter for the next one[/]",
        border_style="magenta",
        padding=(1, 4)
    ))

    # ── Check what's already done ──
    completed = load_completed_repos() if skip_completed else set()
    pending   = [r for r in repos if r not in completed]

    if not pending:
        console.print("\n[green]✔ All repos already processed![/]")
        console.print("[dim]Add more URLs to REPOS list and run again.[/]\n")
        return

    console.print(f"\n[dim]Total repos: {len(repos)}  "
                  f"· Already done: {len(completed)}  "
                  f"· To process: {len(pending)}[/]\n")
    console.print(f"[dim]Current RAG memory: {get_memory_size()} entries[/]")
    console.print(f"[dim]Current dataset:    {get_count()} examples[/]\n")

    # ── Run each repo ──
    start_all      = time.time()
    processed      = 0
    failed         = 0
    total_files    = 0

    for i, repo_url in enumerate(pending, 1):
        try:
            files = process_single_repo(repo_url, i, len(pending))
            if files > 0:
                processed   += 1
                total_files += files
            else:
                failed += 1

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Interrupted by user[/]")
            break

        except Exception as e:
            failed += 1
            console.print(f"  [red]✗ Unexpected error: {e}[/]")
            log_result(repo_url, "error", 0, 0, str(e))

        # Delay between repos
        if i < len(pending):
            time.sleep(DELAY_BETWEEN)

    elapsed = time.time() - start_all
    show_stats(processed, failed, total_files, elapsed)


# =====================================================
# ADD REPOS INTERACTIVELY
# =====================================================

def add_repos_interactive():
    """Let user paste GitHub URLs one by one."""
    console.print("\n[bold cyan]Add GitHub Repository URLs[/]")
    console.print("[dim]Paste one URL per line. Empty line to start.[/]\n")

    custom_repos = []
    while True:
        url = input("  URL (or Enter to start): ").strip()
        if not url:
            break
        if url.startswith("https://github.com/"):
            custom_repos.append(url)
            console.print(f"  [green]✔ Added: {url}[/]")
        else:
            console.print(f"  [red]✗ Invalid URL — must start with https://github.com/[/]")

    if custom_repos:
        console.print(f"\n[dim]Running on {len(custom_repos)} custom repos...[/]")
        run_bulk(repos=custom_repos, skip_completed=False)
    else:
        console.print("[dim]No URLs entered.[/]")


# =====================================================
# MAIN MENU
# =====================================================

if __name__ == "__main__":

    console.print()
    console.print(Panel.fit(
        "[bold magenta]GitHub Bulk Runner[/]\n"
        "[dim]Continuous Learning — feeds repos into RAG + Dataset[/]",
        border_style="magenta",
        padding=(1, 4)
    ))

    console.print("\n[bold]Choose an option:[/]\n")
    console.print("  [cyan]1[/]  Run default repo list (from REPOS variable)")
    console.print("  [cyan]2[/]  Enter custom GitHub URLs interactively")
    console.print("  [cyan]3[/]  Show current stats only\n")

    choice = input("  Enter choice (1/2/3): ").strip()

    if choice == "1":
        run_bulk()

    elif choice == "2":
        add_repos_interactive()

    elif choice == "3":
        console.print()
        console.print(Panel(
            f"[cyan]RAG Memory:[/]  [bold]{get_memory_size()}[/] entries\n"
            f"[yellow]Dataset:[/]     [bold]{get_count()}[/] examples\n"
            f"[green]Fine-tune:[/]   [bold]{'✅ Ready!' if get_count() >= 500 else f'Need {500 - get_count()} more'}[/]",
            title="[bold magenta]📦 Knowledge Base Stats[/]",
            border_style="magenta",
            padding=(1, 2)
        ))

    else:
        console.print("[dim]Invalid choice. Running default list...[/]")
        run_bulk()