import os
import warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
warnings.filterwarnings("ignore")

import chromadb
from sentence_transformers import SentenceTransformer

# =====================================================
# PERSISTENT MEMORY — stores all past explanations
# =====================================================

client     = chromadb.PersistentClient(path="./memory")
collection = client.get_or_create_collection("code_explanations")
embedder   = SentenceTransformer("all-MiniLM-L6-v2")


def save_explanation(file_path, code, explanation):
    """Save a code + explanation pair to memory."""
    try:
        embedding = embedder.encode(code[:1000]).tolist()
        safe_id   = file_path.replace("/", "_").replace("\\", "_").replace(":", "_")

        collection.upsert(
            documents  = [code[:1000]],
            embeddings = [embedding],
            metadatas  = [{
                "file":        file_path,
                "explanation": explanation[:2000]
            }],
            ids = [safe_id]
        )
    except Exception as e:
        print(f"[RAG] Could not save: {e}")


def find_similar(code, n=2):
    """Find the most similar past explanations from memory."""
    try:
        count = collection.count()
        if count == 0:
            return []

        embedding = embedder.encode(code[:1000]).tolist()
        results   = collection.query(
            query_embeddings = [embedding],
            n_results        = min(n, count)
        )

        if results and results["metadatas"]:
            return [m["explanation"] for m in results["metadatas"][0]]

    except Exception as e:
        print(f"[RAG] Could not search: {e}")

    return []


def get_memory_size():
    """How many explanations are stored in memory."""
    try:
        return collection.count()
    except Exception:
        return 0