import json
import os
import shutil
import requests
import sys
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, VectorParams, PointStruct

import os
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.config import (
    OLLAMA_URL,
    EMBEDDING_MODEL as EMBED_MODEL,
    QDRANT_URL,
    VECTOR_SIZE,
    BATCH_SIZE,
    COLLECTIONS,
    CHUNKS_JSON_PATH,
)

def check_services():
    """Check both Ollama and Qdrant are reachable before starting."""
    print("Checking services...")
    
    # Ollama check
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
    except Exception:
        print(f"Error: Ollama is not running. Start it with: ollama serve")
        sys.exit(1)

    # Qdrant check
    try:
        response = requests.get(f"{QDRANT_URL}/healthz", timeout=5)
        response.raise_for_status()
    except Exception:
        print(f"Error: Qdrant is not running. Start it with:\n      docker run -d -p 6333:6333 qdrant/qdrant")
        sys.exit(1)
    
    print("Services are healthy.")

def get_embedding(text: str) -> list[float]:
    """POST to Ollama /api/embeddings for text embedding."""
    # Truncate text to 1000 characters to avoid Ollama 500 errors on long descriptions
    safe_text = text[:1000] if len(text) > 1000 else text
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": safe_text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        safe_snippet = safe_text[:50].encode('cp1251', errors='replace').decode('cp1251')
        print(f"Warning: Failed to get embedding for text: {safe_snippet}... Error: {e}")
        return None

_QDRANT_STORAGE = os.path.join(os.path.dirname(__file__), "..", "..", "qdrant_storage", "collections")

def setup_collections(client: QdrantClient):
    """Ensure all three collections exist and are ready."""
    print("Setting up collections...")
    for collection_name in COLLECTIONS.values():
        if client.collection_exists(collection_name):
            print(f"Collection '{collection_name}' already exists.")
            continue

        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            print(f"Collection '{collection_name}' created.")
        except UnexpectedResponse as e:
            # Orphaned storage dir from a previous interrupted run — wipe and retry
            if b"Collection data already exists" in e.content:
                orphan_dir = os.path.join(_QDRANT_STORAGE, collection_name)
                print(f"Orphaned storage found for '{collection_name}', removing {orphan_dir} and retrying...")
                shutil.rmtree(orphan_dir, ignore_errors=True)
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                print(f"Collection '{collection_name}' created after cleanup.")
            else:
                raise
    print("Collections setup complete.")

def index_chunks(client: QdrantClient, chunks: list):
    """Split chunks by type into groups and index them in batches."""
    groups = {
        "hero": [],
        "hero_build": [],
        "ability": [],
        "item": [],
        "wiki_lore": [],
        "wiki_guide": []
    }

    for chunk in chunks:
        ctype = chunk["metadata"].get("type")
        if ctype in groups:
            groups[ctype].append(chunk)

    counts = {"hero": 0, "ability": 0, "item": 0, "wiki_lore": 0, "wiki_guide": 0}

    # hero_build chunks go into the same heroes collection
    COLLECTION_MAP = {
        "hero":       "deadlock_heroes",
        "hero_build": "deadlock_heroes",
        "ability":    "deadlock_abilities",
        "item":       "deadlock_items",
        "wiki_lore":  "deadlock_lore",
        "wiki_guide": "deadlock_guides",
    }
    COUNT_KEY = {
        "hero":       "hero",
        "hero_build": "hero",
        "ability":    "ability",
        "item":       "item",
        "wiki_lore":  "wiki_lore",
        "wiki_guide": "wiki_guide",
    }

    for ctype, group in groups.items():
        if not group: continue
        collection_name = COLLECTION_MAP[ctype]
        print(f"Indexing {ctype}s into {collection_name}...")

        for i in range(0, len(group), BATCH_SIZE):
            batch = group[i : i + BATCH_SIZE]
            points = []

            for chunk in batch:
                embedding = get_embedding(chunk["text"])
                if embedding is None:
                    continue

                # ID Generation logic (Deterministic using MD5)
                import hashlib
                metadata = chunk["metadata"]
                if ctype == "hero":
                    key = f"hero_{metadata['hero']}"
                elif ctype == "hero_build":
                    key = f"hero_build_{metadata['hero']}"
                elif ctype == "ability":
                    key = f"ability_{metadata['hero']}_{metadata['slot']}"
                elif ctype == "item":
                    item_id = metadata.get('id') or metadata.get('item_id')
                    key = f"item_{item_id}"
                elif ctype == "wiki_lore":
                    key = f"wiki_lore_{metadata.get('hero_name', metadata.get('title'))}"
                elif ctype == "wiki_guide":
                    key = f"wiki_guide_{metadata.get('hero_name', metadata.get('title'))}_{metadata.get('category')}"
                else:
                    key = hashlib.md5(chunk["text"].encode()).hexdigest()

                # Generate a stable 64-bit integer ID from the key string
                point_id = int(hashlib.md5(key.encode()).hexdigest()[:12], 16)
                
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk["text"],
                        **metadata
                    }
                ))
            
            if points:
                client.upsert(collection_name=collection_name, points=points)

            counts[COUNT_KEY[ctype]] += len(points)
            print(f"{ctype}: {counts[COUNT_KEY[ctype]]}/{len(group)} indexed...")

    return counts

def run_test_query(client: QdrantClient):
    """Run a smoke test search after indexing."""
    print("\nRunning smoke test query...")
    query = "hero with fire damage over time"
    embedding = get_embedding(query)
    
    if not embedding:
        print("Smoke test failed: Could not get query embedding.")
        return

    results = client.query_points(
        collection_name=COLLECTIONS["hero"],
        query=embedding,
        limit=3
    ).points

    print(f"Results for '{query}':")
    max_score = 0
    for res in results:
        name = res.payload.get("name", "Unknown")
        text = res.payload.get("text", "")[:100]
        print(f" - [{res.score:.4f}] {name}: {text}...")
        if res.score > max_score:
            max_score = res.score

    assert max_score > 0.5, f"Smoke test failed: Best result score {max_score:.4f} is <= 0.5"
    print("Smoke test passed!")

def main():
    check_services()
    
    print(f"Loading chunks from {CHUNKS_JSON_PATH}...")
    try:
        with open(CHUNKS_JSON_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print(f"Error: {CHUNKS_JSON_PATH} not found.")
        sys.exit(1)

    client = QdrantClient(url=QDRANT_URL)
    setup_collections(client)
    
    counts = index_chunks(client, chunks)
    
    run_test_query(client)
    
    print("\nIndexing complete!")
    print(f"Heroes:    {counts['hero']}")
    print(f"Abilities: {counts['ability']}")
    print(f"Items:     {counts['item']}")
    print(f"Wiki Lore: {counts['wiki_lore']}")
    print(f"Wiki Guides: {counts['wiki_guide']}")
    print(f"Total:     {sum(counts.values())} chunks indexed")

if __name__ == "__main__":
    main()
