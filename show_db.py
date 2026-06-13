#type: ignore
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.columns import Columns

console = Console(force_terminal=True)


def show_rag_memory():
    """Show everything stored in ChromaDB RAG memory."""
    try:
        from rag_memory import collection, get_memory_size

        count = get_memory_size()

        if count == 0:
            console.print("[dim]RAG memory is empty — run main.py on some repos first[/]")
            return

        console.print(Panel(
            f"[bold green]{count}[/] explanations stored in memory",
            title="[bold cyan]🧠 RAG Memory[/]",
            border_style="cyan"
        ))

        # Show all stored entries
        results = collection.get(include=["metadatas"])
        metadatas = results.get("metadatas", [])

        table = Table(
            box=box.ROUNDED,
            border_style="cyan",
            show_header=True,
            header_style="bold cyan",
            padding=(0, 2)
        )
        table.add_column("#",        style="dim",        width=4)
        table.add_column("File",     style="white",      width=40)
        table.add_column("Preview",  style="dim",        width=50)

        for i, meta in enumerate(metadatas, 1):
            file_path   = meta.get("file", "unknown")
            explanation = meta.get("explanation", "")
            preview     = explanation[:80].replace("\n", " ") + "..."
            table.add_row(str(i), file_path.split("/")[-1], preview)

        console.print(table)

    except ImportError:
        console.print("[red]ChromaDB not installed. Run: pip install chromadb[/]")
    except Exception as e:
        console.print(f"[red]Error reading RAG memory: {e}[/]")


def show_dataset():
    """Show everything stored in training_data.jsonl."""
    DATASET_FILE = "training_data.jsonl"

    if not os.path.exists(DATASET_FILE):
        console.print("[dim]No dataset yet — run main.py on some repos first[/]")
        return

    entries = []
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    size_kb = os.path.getsize(DATASET_FILE) / 1024

    console.print(Panel(
        f"[bold green]{len(entries)}[/] training examples  ·  "
        f"[bold yellow]{size_kb:.1f} KB[/]  ·  "
        f"[dim]{DATASET_FILE}[/]",
        title="[bold yellow]📊 Training Dataset[/]",
        border_style="yellow"
    ))

    table = Table(
        box=box.ROUNDED,
        border_style="yellow",
        show_header=True,
        header_style="bold yellow",
        padding=(0, 2)
    )
    table.add_column("#",       style="dim",   width=4)
    table.add_column("File",    style="white", width=30)
    table.add_column("Repo",    style="cyan",  width=30)
    table.add_column("Date",    style="dim",   width=20)
    table.add_column("Preview", style="dim",   width=40)

    for i, entry in enumerate(entries, 1):
        file_path = entry.get("file", "unknown").replace("\\", "/").split("/")[-1]
        repo      = entry.get("repo", "").split("/")[-1] or "—"
        date      = entry.get("date", "")[:10]
        preview   = entry.get("response", "")[:60].replace("\n", " ") + "..."
        table.add_row(str(i), file_path, repo, date, preview)

    console.print(table)


def show_summary():
    """Show a combined summary of both databases."""
    try:
        from rag_memory import get_memory_size
        rag_count = get_memory_size()
    except Exception:
        rag_count = 0

    DATASET_FILE = "training_data.jsonl"
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE) as f:
            dataset_count = sum(1 for _ in f)
        size_kb = os.path.getsize(DATASET_FILE) / 1024
    else:
        dataset_count = 0
        size_kb = 0

    memory_folder = "./memory"
    memory_size_mb = 0
    if os.path.exists(memory_folder):
        for root, dirs, files in os.walk(memory_folder):
            for file in files:
                memory_size_mb += os.path.getsize(os.path.join(root, file))
        memory_size_mb = memory_size_mb / (1024 * 1024)

    table = Table(
        box=box.ROUNDED,
        show_header=False,
        border_style="magenta",
        padding=(0, 3)
    )
    table.add_column("Key",   style="dim cyan",  width=24)
    table.add_column("Value", style="bold white")

    table.add_row("🧠 RAG Memory entries",     f"[green]{rag_count}[/] explanations")
    table.add_row("💾 RAG Memory size",        f"[green]{memory_size_mb:.1f} MB[/]")
    table.add_row("📊 Dataset examples",       f"[yellow]{dataset_count}[/] training pairs")
    table.add_row("📁 Dataset file size",      f"[yellow]{size_kb:.1f} KB[/]")
    table.add_row("📍 RAG location",           "[dim]./memory/[/]")
    table.add_row("📍 Dataset location",       "[dim]./training_data.jsonl[/]")

    fine_tune_ready = "✅ Yes — ready for Colab!" if dataset_count >= 500 else f"❌ Not yet — need {500 - dataset_count} more examples"
    table.add_row("🚀 Fine-tune ready",        fine_tune_ready)

    console.print()
    console.print(Panel(
        table,
        title="[bold magenta]📦  Knowledge Base Overview[/]",
        border_style="magenta",
        padding=(1, 1)
    ))
    console.print()


if __name__ == "__main__":
    console.print()
    console.print("[bold magenta]╔══════════════════════════════════════╗[/]")
    console.print("[bold magenta]║     Knowledge Base Viewer            ║[/]")
    console.print("[bold magenta]╚══════════════════════════════════════╝[/]")
    console.print()

    show_summary()

    console.print("\n[bold cyan]─── RAG Memory Details ───[/]\n")
    show_rag_memory()

    console.print("\n[bold yellow]─── Dataset Details ───[/]\n")
    show_dataset()