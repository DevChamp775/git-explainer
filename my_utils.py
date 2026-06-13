import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console(force_terminal=True)


# =====================================================
# DIVIDER
# =====================================================

def print_divider():
    console.rule(style="dim white")


# =====================================================
# HEADER BANNER
# =====================================================

def print_header():
    console.print()
    console.print(Panel.fit(
        "[bold magenta]  GitHub Repository Explainer  [/]\n"
        "[dim]  Powered by Ollama + DeepSeek + Python  [/]",
        border_style="magenta",
        padding=(1, 6)
    ))
    console.print()


# =====================================================
# REPO INFO TABLE
# =====================================================

def print_repo_info(repo_info):
    table = Table(
        box=box.ROUNDED,
        show_header=False,
        border_style="blue",
        padding=(0, 2),
        expand=False
    )
    table.add_column("Key",   style="dim cyan",  width=16)
    table.add_column("Value", style="bold white")

    table.add_row("Name",        repo_info.get("name", "N/A"))
    table.add_row("Owner",       repo_info["owner"]["login"])
    table.add_row("Stars",       f"[yellow]⭐  {repo_info.get('stargazers_count', 0):,}[/]")
    table.add_row("Forks",       f"[cyan]🍴  {repo_info.get('forks_count', 0):,}[/]")
    table.add_row("Language",    f"[green]{repo_info.get('language') or 'Unknown'}[/]")
    table.add_row("Description", f"[dim]{repo_info.get('description') or 'No description'}[/]")

    console.print(table)
    console.print()
    
#color_language
def print_language_bar(repo_info):
    import requests

    languages_url = repo_info.get("languages_url")
    if not languages_url:
        console.print("[dim]⚠ No languages URL found[/]")
        return

    try:
        from clone_repo import get_headers
        response = requests.get(languages_url, headers=get_headers(), timeout=10)
        langs = response.json()
    except Exception as e:
        console.print(f"[dim]⚠ Could not fetch languages: {e}[/]")
        return

    if not langs:
        console.print("[dim]⚠ No language data returned[/]")
        return

    total = sum(langs.values())

    COLORS = {
        "JavaScript": "yellow",
        "Python":     "blue",
        "HTML":       "red",
        "CSS":        "magenta",
        "TypeScript": "cyan",
        "Java":       "bright_red",
        "C++":        "green",
        "Go":         "cyan",
        "Rust":       "bright_yellow",
        "Julia":      "purple",
        "Ruby":       "red",
        "PHP":        "magenta",
        "Shell":      "green",
    }

    lang_data = []
    for lang, bytes_count in sorted(langs.items(), key=lambda x: -x[1]):
        pct = (bytes_count / total) * 100
        color = COLORS.get(lang, "white")
        lang_data.append((lang, pct, color))

    # colored block bar
    bar = ""
    for lang, pct, color in lang_data:
        blocks = max(1, int(pct / 2))  # minimum 1 block so nothing is hidden
        bar += f"[{color}]{'█' * blocks}[/]"

    console.print(bar)
    console.print()

    # legend
    legend = ""
    for lang, pct, color in lang_data:
        legend += f"[{color}]⬤[/]  [white]{lang}[/] [dim]{pct:.1f}%[/]    "

    console.print(legend)
    console.print()
# =====================================================
# FILE TREE
# =====================================================

def print_file_tree(files):
    console.print(
        f"[bold green]✔[/] [white]Selected[/] "
        f"[bold yellow]{len(files)}[/] [white]file(s) for processing[/]\n"
    )
    for i, f in enumerate(files):
        connector = "└─" if i == len(files) - 1 else "├─"
        try:
            size_kb = os.path.getsize(f) / 1024
            size_str = f"[dim]· {size_kb:.1f} KB[/]"
        except OSError:
            size_str = ""
        console.print(
            f"  [dim]{connector}[/] [green]●[/] "
            f"[white]{short_path(f)}[/] {size_str}"
        )
    console.print()


# =====================================================
# SUMMARY PANEL
# =====================================================

def print_summary_panel(summary):
    console.print(Panel(
        f"[white]{summary}[/]",
        title="[bold cyan]📘  Repository Summary[/]",
        border_style="cyan",
        padding=(1, 2)
    ))
    console.print()


# =====================================================
# FILE EXPLANATION PANEL
# =====================================================

def print_explanation_panel(filename, explanation):
    console.print(Panel(
        f"[white]{explanation}[/]",
        title=f"[bold green]📄  {filename}[/]",
        border_style="green",
        padding=(1, 2)
    ))
    console.print()


# =====================================================
# COMPLETION STATS
# =====================================================

def print_completion(num_files, elapsed):
    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 2)
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value",  style="bold green")

    table.add_row("Files analysed", str(num_files))
    table.add_row("Time elapsed",   f"{elapsed:.1f}s")
    table.add_row("Model used",     "llama3 via Ollama")

    console.print(Panel(
        table,
        title="[bold green]✅  Pipeline Complete[/]",
        border_style="green",
        padding=(0, 1)
    ))
    console.print()

    console.print("[dim]  GitHub Repo  →  API Fetch  →  Clone  →  Extract"
                  "  →  AI Explain  →  Summary  →  Done[/]")
    console.print()


# =====================================================
# SHORT PATH HELPER
# =====================================================

def short_path(path):
    """
    Returns last 3 segments of the path for readable display.
    e.g. /tmp/repo_abc/src/utils/helper.py → src/utils/helper.py
    """
    path = path.replace("\\", "/")
    parts = path.split("/")
    if len(parts) >= 3:
        return "/".join(parts[-3:])
    return path