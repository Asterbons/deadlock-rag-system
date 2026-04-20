# Deadlock RAG

A data pipeline and RAG (Retrieval-Augmented Generation) system for Valve's *Deadlock*. Extracts hero, ability, and item data from raw `.vdata` game files, indexes them as embeddings in Qdrant, and serves a semantic search + LLM-powered query API with a multi-page web UI.

## Setup

No `requirements.txt` — install dependencies manually:

```bash
pip install qdrant-client fastapi uvicorn requests apscheduler
```

**External services required at runtime:**

| Service | Command |
|---|---|
| Qdrant (first run) | `docker run -d --name qdrant -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant` |
| Qdrant (subsequent) | `docker start qdrant` |
| Ollama | `ollama serve` |

Ollama models needed:
```bash
ollama pull mxbai-embed-large   # embeddings
ollama pull qwen2.5:7b          # LLM
```

## Pipeline

The system runs in two phases: **once** to build the knowledge base, and **on every query** at runtime.

### Build phase (run once, or when game data updates)

```bash
# 1. Extract hero + ability data
python src/heroes_abilities_extractor/pipeline.py
python src/heroes_abilities_extractor/hero_profile_extractor.py

# 2. Extract shop/item data
python src/shop_extractor/pipeline.py

# 3. Chunk extracted JSON into RAG-ready pieces
python src/rag/chunker.py

# 4. Embed chunks and load into Qdrant (requires Ollama + Qdrant running)
python src/rag/indexer.py
```

### Keeping data up to date

The updater fetches the latest `.vdata` and localization files from [SteamTracking/GameTracking-Deadlock](https://github.com/SteamTracking/GameTracking-Deadlock) and re-runs the full pipeline if relevant files changed.

**One-shot check** (run manually when needed):
```bash
python -m src.updater.patch_monitor
```

**Auto-scheduler** (checks on a repeating interval):
```bash
python -m src.updater.scheduler
```

Configure the check interval in `src/config.py`:
```python
UPDATE_INTERVAL_HOURS = 6  # supports decimals: 0.5 = 30 min, 24 = daily
```

### Runtime

```bash
# Start the API + web UI
python src/api/server.py
# → http://localhost:8000

# Or use the interactive CLI
python src/rag/rag.py
```

## Web UI

Open `http://localhost:8000` after starting the server.

| Page | URL | Description |
|---|---|---|
| Landing | `/` | Stats overview, nav, tech stack |
| Chat | `/chat` | Streaming AI chat with source citations |
| Heroes | `/heroes` | Browsable hero grid with type filter + search |
| Hero detail | `/heroes/{hero_id}` | Full stats, abilities, weapon, recommended items |
| Items | `/items` | Item browser with slot tabs, tier filter, and search |

Pages link to each other and include "Ask AI" shortcuts that pre-fill the chat with a relevant question.

## How it works

```
data/raw/*.vdata + localization .txt
        ↓  Extraction
data/processed/processed_heroes.json   (38 heroes + 152 abilities)
data/processed/shop.json               (171 items)
data/processed/heroes_index.json       (cross-hero summary)
        ↓  Chunking  (src/rag/chunker.py)
data/processed/chunks.json             (399 semantic chunks)
        ↓  Indexing  (src/rag/indexer.py → mxbai-embed-large via Ollama)
Qdrant collections:
  deadlock_heroes     (76 points: 38 stats + 38 build guides)
  deadlock_abilities  (152 points)
  deadlock_items      (171 points)
        ↓  Query time
src/rag/router.py    → classifies question, picks collections
src/rag/retriever.py → embeds query, searches Qdrant, returns top chunks
src/rag/rag.py       → builds prompt, calls LLM (streaming)
src/api/server.py    → FastAPI, SSE streaming to web UI
```

**Why each piece exists:**

| Component | Purpose |
|---|---|
| Extractors | Converts unreadable `.vdata` to clean JSON |
| Chunker | Splits JSON into semantic chunks: two per hero (stats chunk + build guide chunk with recommended items), one per ability, one per item |
| Indexer | Converts text chunks to 1024-dim vectors via `mxbai-embed-large` |
| Qdrant | Stores vectors + full text payloads; enables cosine similarity search |
| Router | Classifies the query to pick the right collections and apply hero filters |
| Retriever | Finds the top-k most semantically relevant chunks for a query |
| LLM | Reads retrieved chunks as context, generates a grounded answer |

## Project Structure

```
dlrag/
├── data/
│   ├── raw/                          # Valve .vdata + localization .txt files
│   └── processed/
│       ├── chunks.json               # 399 RAG-ready chunks
│       ├── heroes_index.json         # Summary of all 38 heroes
│       ├── processed_heroes.json     # Unified hero + ability data
│       ├── shop.json                 # All items
│       └── heroes/                   # Per-hero JSON files (38 files)
├── src/
│   ├── heroes_abilities_extractor/
│   │   ├── kv3_parser.py             # Custom KV3 recursive-descent parser
│   │   ├── hero_extractor.py         # Hero stat extraction with hero_base inheritance
│   │   ├── ability_enricher.py       # Ability enrichment + semantic tags
│   │   ├── pipeline.py               # Hero/ability extraction entrypoint
│   │   └── hero_profile_extractor.py # Per-hero profile files
│   ├── shop_extractor/
│   │   ├── shop_builder.py           # Item extraction + stat normalization
│   │   └── pipeline.py               # Shop extraction entrypoint
│   ├── rag/
│   │   ├── chunker.py                # Produces chunks.json
│   │   ├── indexer.py                # Loads chunks into Qdrant
│   │   ├── retriever.py              # Embeds query + searches Qdrant
│   │   ├── router.py                 # Query classification
│   │   └── rag.py                    # Full RAG pipeline + streaming
│   ├── api/
│   │   └── server.py                 # FastAPI server + page routes + REST API
│   ├── web/
│   │   ├── landing.html              # Home page with live stats
│   │   ├── chat.html                 # Streaming chat UI
│   │   ├── heroes.html               # Hero browser (filter + search)
│   │   ├── hero_detail.html          # Per-hero detail page
│   │   └── items.html                # Item browser (slot + tier + search)
│   ├── updater/
│   │   ├── patch_monitor.py          # GitHub polling + file download
│   │   ├── update_pipeline.py        # Runs full extraction → index pipeline
│   │   └── scheduler.py              # APScheduler-based auto-update loop
│   ├── config.py                     # Centralized file paths + update interval
│   └── mapping_handler.py            # MODIFIER_VALUE_* → clean stat names
└── tests/
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Checks Ollama + Qdrant connectivity |
| `GET /api/stats` | Hero, ability, and item counts |
| `GET /api/heroes` | All heroes; optional `?type=Marksman` filter |
| `GET /api/heroes/{hero_id}` | Full hero object with abilities and weapon stats |
| `GET /api/items` | All items; optional `?slot=weapon` and `?tier=2` filters |
| `GET /api/items/{item_id}` | Single item by ID |
| `POST /api/ask` | Streaming SSE RAG query (request body: `{question, history}`) |

## Key concepts

**Embedding** — `mxbai-embed-large` converts text to a 1024-dimensional vector. Semantically similar texts produce mathematically close vectors, enabling search without keyword matching.

**Cosine similarity** — Qdrant ranks results by how closely their vectors point in the same direction as the query vector. Score 1.0 = identical meaning, 0.0 = unrelated.

**Payload** — Full original text stored alongside each vector in Qdrant. The vector finds the right chunk; the payload is what the LLM reads as context.

**Truncation** — Chunks longer than 1000 characters are truncated before embedding (model limit), but the full text is always stored in the payload and sent to the LLM.
