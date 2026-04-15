import os
import sys
import json
import asyncio
import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the project root to sys.path to allow importing src.*
# This ensures that src.rag.retriever and src.rag.rag can be found
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.rag.retriever import retrieve, format_context
from src.rag.rag import ask_stream, build_prompt, OLLAMA_URL, LLM_MODEL

app = FastAPI(title="Deadlock RAG Backend")


class AskRequest(BaseModel):
    question: str
    history: list[dict] = []

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Qdrant URL for health check (not imported from retriever but used there)
QDRANT_URL = "http://localhost:6333"

@app.get("/api/health")
def health_check():
    """Check both Ollama and Qdrant are reachable."""
    ollama_ok = False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1)
        ollama_ok = r.status_code == 200
    except:
        pass

    qdrant_ok = False
    try:
        r = requests.get(f"{QDRANT_URL}/healthz", timeout=1)
        qdrant_ok = r.status_code == 200
    except:
        pass

    return {
        "status": "ok",
        "ollama": ollama_ok,
        "qdrant": qdrant_ok
    }

@app.get("/api/heroes")
def get_heroes():
    """Return list of all heroes from heroes_index.json."""
    index_path = os.path.join(PROJ_ROOT, "data", "processed", "heroes_index.json")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.post("/api/ask")
async def ask_rag(request: AskRequest):
    """Main streaming endpoint for RAG queries."""
    import time

    def event_stream():
        _t0 = time.time()
        print(f"[DEBUG server] /api/ask event_stream started: {request.question!r}", flush=True)
        try:
            for msg_type, content in ask_stream(request.question, request.history):
                if msg_type == "token":
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                elif msg_type == "sources":
                    print(f"[DEBUG server] sending sources ({len(content)} results) at {time.time()-_t0:.2f}s", flush=True)
                    # Sources event — compute display label per source type
                    sources_data = []
                    for r in content:
                        meta  = r["metadata"]
                        ctype = r["type"]
                        if ctype == "hero":
                            label = meta.get("name", meta.get("hero", "Unknown"))
                        elif ctype == "ability":
                            hero_name    = meta.get("hero_name", meta.get("hero", ""))
                            ability_name = meta.get("name", "Unknown Ability")
                            label = f"{ability_name} ({hero_name})"
                        elif ctype == "item":
                            label = meta.get("name", meta.get("id", "Unknown"))
                        else:
                            label = meta.get("name", "Unknown")
                        sources_data.append({
                            "score":    round(r["score"], 4),
                            "type":     ctype,
                            "label":    label,
                            "metadata": meta,
                        })
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"

            print(f"[DEBUG server] event_stream done at {time.time()-_t0:.2f}s, sending 'done'", flush=True)
            yield 'data: {"type": "done"}\n\n'

        except Exception as e:
            print(f"[DEBUG server] event_stream error at {time.time()-_t0:.2f}s: {e}", flush=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Static files setup
WEB_DIR = os.path.join(PROJ_ROOT, "src", "web")
if not os.path.exists(WEB_DIR):
    os.makedirs(WEB_DIR, exist_ok=True)

# index.html served at root /
@app.get("/")
def serve_home():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Web UI directory found but index.html is missing."}

# Mount src/web/ as static files directory
app.mount("/", StaticFiles(directory=WEB_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
