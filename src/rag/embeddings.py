"""Shared embedding + service-health helpers used by both retriever and indexer."""
import os
import sys

import requests

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.config import OLLAMA_URL, EMBEDDING_MODEL, QDRANT_URL, EMBEDDING_TRUNCATE_CHARS


def check_services() -> None:
    """Verify Ollama and Qdrant are reachable. Exits with code 1 on failure."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
    except Exception:
        print(f"Error: Ollama is not running at {OLLAMA_URL}. Start it with: 'ollama serve'")
        sys.exit(1)

    try:
        response = requests.get(f"{QDRANT_URL}/healthz", timeout=5)
        response.raise_for_status()
    except Exception:
        print("Error: Qdrant is not running. Start it with:\n      docker run -d -p 6333:6333 qdrant/qdrant")
        sys.exit(1)


def get_embedding(text: str) -> list[float]:
    """POST to Ollama /api/embeddings. Raises RuntimeError on failure."""
    safe_text = text[:EMBEDDING_TRUNCATE_CHARS]
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": safe_text},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        raise RuntimeError(f"Failed to get embedding: {e}") from e
