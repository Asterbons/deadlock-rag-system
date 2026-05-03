import json
import logging
import os
import shutil
import sys
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, VectorParams, PointStruct

import os
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.config import (
    QDRANT_URL,
    VECTOR_SIZE,
    BATCH_SIZE,
    COLLECTIONS,
    CHUNKS_JSON_PATH,
)
from src.rag.embeddings import get_embedding, check_services

logger = logging.getLogger(__name__)

_QDRANT_STORAGE = os.path.join(os.path.dirname(__file__), "..", "..", "qdrant_storage", "collections")

def setup_collections(client: QdrantClient):
    """Ensure all three collections exist and are ready."""
    logger.info("Setting up collections...")
    for collection_name in COLLECTIONS.values():
        if client.collection_exists(collection_name):
            logger.info("Collection '%s' already exists.", collection_name)
            continue

        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info("Collection '%s' created.", collection_name)
        except UnexpectedResponse as e:
            # Orphaned storage dir from a previous interrupted run — wipe and retry
            if b"Collection data already exists" in e.content:
                orphan_dir = os.path.join(_QDRANT_STORAGE, collection_name)
                logger.warning("Orphaned storage found for '%s', removing %s and retrying...", collection_name, orphan_dir)
                shutil.rmtree(orphan_dir, ignore_errors=True)
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                logger.info("Collection '%s' created after cleanup.", collection_name)
            else:
                raise
    logger.info("Collections setup complete.")

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

    counts = {
        "hero": 0,
        "hero_build": 0,
        "ability": 0,
        "item": 0,
        "wiki_lore": 0,
        "wiki_guide": 0,
    }

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
        "hero_build": "hero_build",
        "ability":    "ability",
        "item":       "item",
        "wiki_lore":  "wiki_lore",
        "wiki_guide": "wiki_guide",
    }

    for ctype, group in groups.items():
        if not group: continue
        collection_name = COLLECTION_MAP[ctype]
        logger.info("Indexing %ss into %s...", ctype, collection_name)

        for i in range(0, len(group), BATCH_SIZE):
            batch = group[i : i + BATCH_SIZE]
            points = []

            for chunk in batch:
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

                try:
                    embedding = get_embedding(chunk["text"])
                except RuntimeError as e:
                    raise RuntimeError(f"Failed embedding chunk {ctype}:{key}") from e

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
            logger.info("%s: %d/%d indexed...", ctype, counts[COUNT_KEY[ctype]], len(group))

    return counts

def run_test_query(client: QdrantClient):
    """Run a smoke test search after indexing."""
    logger.info("Running smoke test query...")
    query = "hero with fire damage over time"
    embedding = get_embedding(query)

    results = client.query_points(
        collection_name=COLLECTIONS["hero"],
        query=embedding,
        limit=3
    ).points

    logger.info("Results for '%s':", query)
    max_score = 0
    for res in results:
        name = res.payload.get("name", "Unknown")
        text = res.payload.get("text", "")[:100]
        logger.info(" - [%.4f] %s: %s...", res.score, name, text)
        if res.score > max_score:
            max_score = res.score

    assert max_score > 0.5, f"Smoke test failed: Best result score {max_score:.4f} is <= 0.5"
    logger.info("Smoke test passed!")

def main():
    check_services()

    logger.info("Loading chunks from %s...", CHUNKS_JSON_PATH)
    try:
        with open(CHUNKS_JSON_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except FileNotFoundError:
        logger.error("%s not found.", CHUNKS_JSON_PATH)
        sys.exit(1)

    client = QdrantClient(url=QDRANT_URL)
    try:
        setup_collections(client)

        counts = index_chunks(client, chunks)

        run_test_query(client)

        logger.info("Indexing complete!")
        logger.info("Heroes:      %d", counts['hero'])
        logger.info("Hero Builds: %d", counts['hero_build'])
        logger.info("Abilities:   %d", counts['ability'])
        logger.info("Items:       %d", counts['item'])
        logger.info("Wiki Lore:   %d", counts['wiki_lore'])
        logger.info("Wiki Guides: %d", counts['wiki_guide'])
        logger.info("Total:       %d chunks indexed", sum(counts.values()))
    finally:
        client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
