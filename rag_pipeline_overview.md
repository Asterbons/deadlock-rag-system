# Deadlock RAG Pipeline Overview

## How to Start Qdrant

Qdrant must be running before you use the retriever or indexer.

First time (creates the container):
```bash
docker run -d --name qdrant -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

Every time after that (container already exists):
```bash
docker start qdrant
```

Check it's running:
```bash
curl http://localhost:6333/healthz
```

---

## The Full Pipeline

The system is built in five stages. The first four run once (or when game data updates). Only the last two run on every user query.

### Stage 1 — Extractors
`hero_profile_extractor.py` and `shop_builder.py` read the raw game files (`heroes.vdata`, `abilities.vdata`, shop localization files) and produce clean structured JSON files — one file per hero, plus a shop file with all items. Think of this as a journalist reading the game source files and writing structured articles about every hero and item.

### Stage 2 — Chunker
`chunker.py` reads all the JSON files produced by the extractors and slices them into small, self-contained pieces called chunks. Each chunk represents exactly one thing: one hero, one ability, or one item. Every chunk has two parts: a `text` field (human-readable string that describes the chunk) and a `metadata` field (structured data like type, hero name, slot, tier). Think of this as an editor cutting long articles into index cards — one card per topic.

### Stage 3 — Indexer
`indexer.py` reads `chunks.json` and loads all 361 chunks into Qdrant. For each chunk it sends the text to Ollama (`mxbai-embed-large`) which returns an embedding — a list of 1024 numbers that mathematically represents the meaning of the text. This embedding (the vector) plus the full original text (the payload) are stored together in Qdrant as a single point. This stage runs once and the data persists between restarts. Think of this as a librarian who reads every index card, understands its meaning, and places it on the shelf in the right location based on that meaning.

### Stage 4 — Qdrant (Vector Database)
After indexing, Qdrant holds three collections: `deadlock_heroes` (38 points), `deadlock_abilities` (152 points), and `deadlock_items` (171 points). Each point contains a vector (for search) and a payload (the full text, returned with results). The vector is what enables semantic search — finding relevant content even when the exact words don't match. Qdrant must be running whenever the retriever is used.

### Stage 5 — Retriever
`retriever.py` runs on every user query. It takes the question, sends it to Ollama to get an embedding, then asks Qdrant to find the vectors most similar to the query vector. Qdrant returns the top matches along with their payloads (full text). The retriever merges results from all three collections, sorts by score, and returns the top 3. Think of this as a search assistant who translates your question into coordinates and finds the three closest index cards on the shelf.

### Stage 6 — LLM (next step)
The retriever's output — 3 relevant chunks of text — is injected into a prompt alongside the user's question and sent to an LLM (Claude, GPT, or a local model via Ollama). The LLM reads the context and generates a precise answer. The LLM contributes reasoning and language; the data comes entirely from your extracted game files. This is what makes RAG better than asking an LLM directly — the LLM always has accurate, up-to-date Deadlock data as a reference.

---

## Run Order

```
Once (or on data update):
  python src/heroes_abilities_extractor/pipeline.py
  python src/shop_extractor/pipeline.py
  python src/rag/chunker.py
  python src/rag/indexer.py

On every query:
  retriever.retrieve(query)  →  LLM
```

---

## Why Each Piece Exists

| Component | Problem it solves |
|---|---|
| Extractors | Raw vdata is unreadable — converts to clean JSON |
| Chunker | JSON files are too large to embed as one unit — splits into searchable pieces |
| Indexer | JSON can't be searched semantically — converts to vectors |
| Qdrant | Stores vectors and enables fast similarity search across 361 chunks |
| Retriever | Finds the 3 most relevant chunks for any question — without keyword matching |
| LLM | Turns raw chunk text into a coherent, natural language answer |

---

## Key Concepts

**Embedding** — a list of 1024 numbers produced by `mxbai-embed-large` that represents the meaning of a text. Similar meanings produce mathematically close vectors.

**Vector search** — instead of matching keywords, Qdrant compares vectors using Cosine similarity and returns the closest ones. This is why "hero with fire" finds Infernus even if "fire" isn't in the chunk text.

**Payload** — the full original text stored alongside the vector in Qdrant. The vector is used to find the right chunk; the payload is what gets sent to the LLM as context.

**Truncation** — `mxbai-embed-large` has a token limit (~512 tokens). Chunks longer than 1000 characters are truncated before embedding, but the full text is always stored in the payload. The LLM always sees the complete data.

**Cosine similarity** — the distance metric used to compare vectors. A score of 1.0 means identical meaning, 0.0 means completely unrelated. In practice, a score above 0.5 is considered a good match.
