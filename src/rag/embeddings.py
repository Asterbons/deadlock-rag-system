"""Shared embedding + service-health helpers used by both retriever and indexer."""
import os
import sys
import unicodedata

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


def _request_embedding(prompt: str) -> list[float]:
    """POST one prompt to Ollama and return the embedding vector."""
    response = None
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": prompt},
            timeout=30,
        )
        response.raise_for_status()
    except Exception as e:
        detail = getattr(response, "text", "")
        if detail:
            raise RuntimeError(f"{e}; response body: {detail[:300]}") from e
        raise RuntimeError(str(e)) from e

    try:
        return response.json()["embedding"]
    except Exception as e:
        raise RuntimeError(f"Invalid embedding response: {e}") from e


def _ascii_fallback_prompt(text: str) -> str:
    """Build an ASCII-only prompt for Ollama models that reject Unicode-heavy input."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text[:EMBEDDING_TRUNCATE_CHARS].strip()


def get_embedding(text: str) -> list[float]:
    """POST to Ollama /api/embeddings. Raises RuntimeError on failure."""
    text = str(text or "")
    safe_text = text[:EMBEDDING_TRUNCATE_CHARS].strip()
    if not safe_text:
        raise RuntimeError("Failed to get embedding: empty text")

    try:
        return _request_embedding(safe_text)
    except RuntimeError as first_error:
        fallback_text = _ascii_fallback_prompt(text)
        if fallback_text and fallback_text != safe_text:
            try:
                return _request_embedding(fallback_text)
            except RuntimeError as fallback_error:
                raise RuntimeError(
                    f"Failed to get embedding after ASCII fallback: {fallback_error}"
                ) from fallback_error
        raise RuntimeError(f"Failed to get embedding: {first_error}") from first_error
