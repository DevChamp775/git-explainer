import time
import shutil

from clone_repo import clone_repo, fetch_repository_info
from file_extractor import get_code_files, get_important_files
from reader import read_file
from ai_explainer import explain_file, summarize_repo, check_ollama
from my_utils import (
    console,
    print_divider,
    print_header,
    print_repo_info,
    print_language_bar,
    print_file_tree,
    print_summary_panel,
    print_explanation_panel,
    print_completion,
    short_path
)

# =====================================================
# CONFIGURATION
# =====================================================

CODE_PREVIEW  = 5000
EXPLAIN_LIMIT = 8000


# =====================================================
# MAIN PROCESS FUNCTION
# =====================================================

def process_repo(repo_url):

    print_header()

    # =================================================
    # PRE-CHECK : OLLAMA STATUS
    # =================================================

    console.print("[dim]Checking Ollama connection...[/]")

    if not check_ollama():
        console.print("\n[bold red]❌ Ollama is NOT running.[/]")
        console.print("[dim]   Start with : ollama serve[/]")
        console.print("[dim]   Pull model : ollama pull deepseek-coder[/]\n")
        return

    console.print(
        "[bold green]✔[/] Ollama is running "
        "[dim]·[/] "
        "model: [bold yellow]deepseek-coder[/]\n"
    )

    # =================================================
    # CLEAN URL
    # =================================================

    repo_url = repo_url.strip().rstrip("/")

    # =================================================
    # STEP 1 : FETCH REPOSITORY INFO
    # =================================================

    print_divider()
    console.print("\n[bold blue]🔎  STEP 1 — FETCHING REPOSITORY INFO[/]\n")

    repo_info = fetch_repository_info(repo_url)

    if repo_info is None:
        console.print("[bold red]❌ Failed to fetch repository info.[/]")
        return

    console.print("[bold green]✔[/] Repository found\n")
    print_repo_info(repo_info)
    print_language_bar(repo_info)

    # =================================================
    # STEP 2 : CLONE REPOSITORY
    # =================================================

    print_divider()
    console.print("\n[bold blue]📥  STEP 2 — CLONING REPOSITORY[/]\n")

    with console.status("[yellow]Cloning repository...[/]", spinner="dots"):
        repo_path = clone_repo(repo_url)

    if not repo_path:
        console.print("[bold red]❌ Repository cloning failed.[/]")
        return

    console.print("[bold green]✔[/] Repository cloned successfully")
    console.print(f"[dim]   Path: {repo_path}[/]\n")

    start_time = time.time()

    try:
        _run_pipeline(repo_path, start_time, repo_url)
    finally:
        print_divider()
        console.print("[dim]🧹 Cleaning up temp folder...[/]")
        shutil.rmtree(repo_path, ignore_errors=True)
        console.print("[dim]✔  Cleanup done[/]\n")


# =====================================================
# PIPELINE — separated so cleanup always runs
# =====================================================

def _run_pipeline(repo_path, start_time, repo_url=""):

    # =================================================
    # STEP 3 : EXTRACT SOURCE CODE FILES
    # =================================================

    print_divider()
    console.print("\n[bold blue]📂  STEP 3 — EXTRACTING SOURCE CODE FILES[/]\n")

    files = get_code_files(repo_path)

    if not files:
        console.print("[bold red]❌ No supported source code files found.[/]")
        return

    # ── Auto-scale based on repo size ──
    if len(files) > 100:
        MAX_FILES = 20
    elif len(files) > 50:
        MAX_FILES = 15
    else:
        MAX_FILES = 10

    console.print(
        f"[bold green]✔[/] Total files detected: "
        f"[bold yellow]{len(files)}[/]  "
        f"[dim]· selecting top {MAX_FILES}[/]"
    )

    selected = get_important_files(files, MAX_FILES)
    print_file_tree(selected)

    # =================================================
    # STEP 4 : COMBINE CODE FOR SUMMARY
    # =================================================

    print_divider()
    console.print("\n[bold blue]📦  STEP 4 — PREPARING REPOSITORY DATA[/]\n")

    combined_code = ""

    for file in selected:
        code = read_file(file)
        if not code.strip():
            continue
        combined_code += f"\n\n### FILE: {short_path(file)}\n"
        combined_code += code[:CODE_PREVIEW]
        combined_code += "\n"

    if not combined_code.strip():
        console.print("[bold red]❌ All selected files were empty.[/]")
        return

    console.print(
        f"[bold green]✔[/] Combined "
        f"[bold yellow]{len(selected)}[/] "
        "file(s) for summary\n"
    )

    # =================================================
    # STEP 5 : GENERATE REPOSITORY SUMMARY
    # =================================================

    print_divider()
    console.print("\n[bold blue]📘  STEP 5 — GENERATING REPOSITORY SUMMARY[/]\n")

    summary = summarize_repo(combined_code)
    print_summary_panel(summary)

    # =================================================
    # STEP 6 : FILE-WISE AI EXPLANATION
    # =================================================

    print_divider()
    console.print("\n[bold blue]🧠  STEP 6 — GENERATING FILE EXPLANATIONS[/]\n")

    for idx, file in enumerate(selected, 1):

        console.print(
            f"[dim]  ({idx}/{len(selected)})[/] "
            f"[white]{short_path(file)}[/]"
        )

        code = read_file(file)

        if not code.strip():
            console.print("[dim]  ⚠  Empty file — skipped[/]\n")
            continue

        explanation = explain_file(
            code[:EXPLAIN_LIMIT],
            file_path=file,
            repo_url=repo_url
        )

        print_explanation_panel(short_path(file), explanation)

    # =================================================
    # STEP 7 : SHOW DB STATS + FINAL OUTPUT
    # =================================================

    elapsed = time.time() - start_time

    # ── Show knowledge base stats ──
    try:
        from rag_memory import get_memory_size
        from dataset_saver import get_count
        rag   = get_memory_size()
        dset  = get_count()
        ready = "✅ Ready!" if dset >= 500 else f"Need {500 - dset} more"
        console.print(
            f"\n[dim]  🧠 RAG Memory: [cyan]{rag}[/] entries  "
            f"· 📊 Dataset: [yellow]{dset}[/] examples  "
            f"· 🚀 Fine-tune: {ready}[/]\n"
        )
    except Exception:
        pass

    print_divider()
    print_completion(len(selected), elapsed)


# =====================================================
# MAIN DRIVER
# =====================================================

if __name__ == "__main__":

    repo = console.input(
        "\n[bold cyan]🔗  Enter GitHub Repository URL:[/]  "
    ).strip()

    if not repo:
        console.print("\n[bold red]❌ No URL entered. Exiting.[/]\n")
    else:
        process_repo(repo)