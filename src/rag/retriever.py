import requests
import sys
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

import os
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.config import (
    QDRANT_URL,
    DEFAULT_TOP_K,
    COLLECTIONS,
)
from src.rag.embeddings import get_embedding, check_services

_client: QdrantClient | None = None


def _qdrant_startup_hint() -> str:
    return "You forgot to launch Docker with Qdrant."


def _ensure_qdrant_running() -> None:
    try:
        response = requests.get(f"{QDRANT_URL}/healthz", timeout=2)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(_qdrant_startup_hint()) from exc


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _ensure_qdrant_running()
        _client = QdrantClient(url=QDRANT_URL, check_compatibility=False)
    return _client

def search_collection(
    client: QdrantClient,
    query_vector: list[float],
    collection: str,
    top_k: int,
    filters: dict = None
) -> list[dict]:
    """Search a single Qdrant collection."""
    
    # Build Qdrant Filter from filters dict if provided
    q_filter = None
    if filters:
        conditions = []
        for key, value in filters.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        q_filter = Filter(must=conditions)
    
    # Using query_points (newer API, matches indexer.py)
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        query_filter=q_filter,
        limit=top_k
    ).points
    
    formatted_results = []
    for res in results:
        formatted_results.append({
            "score":    res.score,
            "type":     res.payload.get("type"),
            "text":     res.payload.get("text"),
            "metadata": res.payload
        })
    return formatted_results

def retrieve(
    query: str,
    collections: list[str] = None,  # None = search all three
    top_k: int = DEFAULT_TOP_K,
    filters: dict = None
) -> list[dict]:
    """Main retrieval function."""
    client = get_qdrant_client()
    query_vector = get_embedding(query)
    
    # collections validation: must be keys from COLLECTIONS ('hero', 'ability', 'item')
    if collections:
        for c in collections:
            if c not in COLLECTIONS:
                raise ValueError(f"Unknown collection '{c}'. Valid options: {list(COLLECTIONS.keys())}")
    
    # default: search all three
    selected_keys = collections if collections else list(COLLECTIONS.keys())
    
    all_results = []
    for key in selected_keys:
        if key in COLLECTIONS:
            import time
            collection_name = COLLECTIONS[key]
            _t0 = time.time()
            print(f"[DEBUG retriever] searching collection '{collection_name}'...", flush=True)
            results = search_collection(client, query_vector, collection_name, top_k, filters)
            print(f"[DEBUG retriever] '{collection_name}' returned {len(results)} results in {time.time()-_t0:.2f}s", flush=True)
            all_results.extend(results)
            
    # Merge all results into one list and sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top_k results overall
    return all_results[:top_k]

def format_context(results: list[dict]) -> str:
    """Format retrieval results into a clean context string."""
    parts = []
    for r in results:
        meta = r["metadata"]
        score = r["score"]
        ctype = r["type"]
        
        if ctype == "hero":
            label = f"Hero: {meta.get('name', meta.get('hero'))}"
        elif ctype == "hero_build":
            label = f"Hero Build Guide: {meta.get('name', meta.get('hero'))}"
        elif ctype == "ability":
            label = f"Ability: {meta.get('name')} ({meta.get('hero')}, slot {meta.get('slot')})"
        elif ctype == "item":
            label = f"Item: {meta.get('name')}"
        elif ctype == "wiki_lore":
            label = f"Lore: {meta.get('hero_name', meta.get('title'))}"
        elif ctype == "wiki_guide":
            label = f"Guide: {meta.get('hero_name', meta.get('title'))}"
        else:
            label = f"{ctype.capitalize()}: {meta.get('name', 'Unknown')}"
            
        header = f"=== {label} [score: {score:.2f}] ==="
        parts.append(f"{header}\n{r['text']}")
        
    return "\n\n".join(parts)

def main():
    print("Deadlock RAG Retriever — type your query, 'quit' to exit")
    while True:
        try:
            query = input("\nQuery: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
            
        if query.lower() == "quit":
            break
        if not query:
            continue
            
        try:
            results = retrieve(query, top_k=3)
            print(f"\nTop {len(results)} results:")
            for i, r in enumerate(results, 1):
                meta = r["metadata"]
                label = meta.get("name") or meta.get("hero") or meta.get("id")
                print(f"  {i}. [{r['score']:.3f}] {r['type'].upper()}: {label}")
            
            print("\n--- Context ---")
            print(format_context(results))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_services()
    main()
