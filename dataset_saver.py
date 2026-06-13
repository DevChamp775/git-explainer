import json
import os
from datetime import datetime

# =====================================================
# AUTO DATASET BUILDER
# =====================================================

DATASET_FILE = "training_data.jsonl"


def save_example(code, explanation, repo_url="", file_path=""):
    """Save one code + explanation pair to the dataset."""
    try:
        entry = {
            "instruction": f"Explain this code file clearly:\n\n{code[:8000]}",
            "response":    explanation,
            "repo":        repo_url,
            "file":        file_path,
            "date":        datetime.now().isoformat()
        }
        with open(DATASET_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[Dataset] Could not save: {e}")


def get_count():
    """How many training examples collected so far."""
    if not os.path.exists(DATASET_FILE):
        return 0
    try:
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def show_stats():
    """Print dataset stats to terminal."""
    count = get_count()
    size  = (
        os.path.getsize(DATASET_FILE) / 1024
        if os.path.exists(DATASET_FILE)
        else 0
    )
    print(
        f"\n📊 Dataset: {count} examples "
        f"· {size:.1f} KB "
        f"· {DATASET_FILE}"
    )