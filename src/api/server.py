import os
import sys
import json
from langchain_community.callbacks import get_openai_callback
import glob
import asyncio
import requests
import uvicorn
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.rag.retriever import retrieve, format_context
from src.rag.rag import ask_stream, build_prompt
from src.config import OLLAMA_URL, LLM_MODEL, EMBEDDING_MODEL

app = FastAPI(title="Deadlock RAG Backend")


class AskRequest(BaseModel):
    question: str
    history: list[dict] = []


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QDRANT_URL = "http://localhost:6333"
DATA_DIR = os.path.join(PROJ_ROOT, "data", "processed")
WEB_DIR = os.path.join(PROJ_ROOT, "src", "web")


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _heroes_index():
    return _load_json(os.path.join(DATA_DIR, "heroes_index.json"))


def _shop():
    return _load_json(os.path.join(DATA_DIR, "shop.json"))


def _serve(filename: str) -> FileResponse:
    path = os.path.join(WEB_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    return FileResponse(path)


# ── Page routes ──────────────────────────────────────────────────────────────

@app.get("/")
def serve_landing():
    return _serve("landing.html")

@app.get("/chat")
def serve_chat():
    return _serve("chat.html")

@app.get("/heroes")
def serve_heroes_page():
    return _serve("heroes.html")

@app.get("/heroes/{hero_id}")
def serve_hero_detail(hero_id: str):
    return _serve("hero_detail.html")

@app.get("/items")
def serve_items_page():
    return _serve("items.html")


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    ollama_ok = False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1)
        ollama_ok = r.status_code == 200
    except Exception:
        pass

    qdrant_ok = False
    try:
        r = requests.get(f"{QDRANT_URL}/healthz", timeout=1)
        qdrant_ok = r.status_code == 200
    except Exception:
        pass

    return {"status": "ok", "ollama": ollama_ok, "qdrant": qdrant_ok}


@app.get("/api/stats")
def get_stats():
    heroes_count = 0
    abilities_count = 0
    items_count = 0
    last_updated = None

    index_path = os.path.join(DATA_DIR, "heroes_index.json")
    if os.path.exists(index_path):
        heroes_count = len(_load_json(index_path))

    chunks_path = os.path.join(DATA_DIR, "chunks.json")
    if os.path.exists(chunks_path):
        chunks = _load_json(chunks_path)
        for chunk in chunks:
            t = chunk.get("metadata", {}).get("type", "")
            if t == "ability":
                abilities_count += 1
            elif t == "item":
                items_count += 1

    # Fallback: count items from shop.json if chunks gave 0
    if items_count == 0:
        shop_path = os.path.join(DATA_DIR, "shop.json")
        if os.path.exists(shop_path):
            shop = _load_json(shop_path)
            for slot in ("weapon", "vitality", "spirit"):
                items_count += len(shop.get(slot, []))

    sha_path = os.path.join(PROJ_ROOT, "data", ".last_commit_sha")
    if os.path.exists(sha_path):
        from datetime import datetime
        ts = os.path.getmtime(sha_path)
        last_updated = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

    return {
        "heroes": heroes_count,
        "abilities": abilities_count,
        "items": items_count,
        "last_updated": last_updated,
        "llm_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
    }


@app.get("/api/heroes")
def get_heroes(type: Optional[str] = None):
    index_path = os.path.join(DATA_DIR, "heroes_index.json")
    if not os.path.exists(index_path):
        return []
    heroes = _load_json(index_path)
    if type:
        heroes = [h for h in heroes if h.get("hero_type", "").lower() == type.lower()]
    return heroes


@app.get("/api/heroes/{hero_id}")
def get_hero(hero_id: str):
    index_path = os.path.join(DATA_DIR, "heroes_index.json")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="heroes_index.json not found")

    heroes = _load_json(index_path)
    entry = next((h for h in heroes if h.get("hero") == hero_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Hero '{hero_id}' not found")

    name = entry.get("name", "")
    filename = name.lower().replace(" ", "_") + ".json"
    hero_path = os.path.join(DATA_DIR, "heroes", filename)
    if not os.path.exists(hero_path):
        raise HTTPException(status_code=404, detail=f"Hero file '{filename}' not found")

    return _load_json(hero_path)


@app.get("/api/items")
def get_items(slot: Optional[str] = None, tier: Optional[int] = None):
    shop_path = os.path.join(DATA_DIR, "shop.json")
    if not os.path.exists(shop_path):
        return []
    shop = _load_json(shop_path)

    slots = ("weapon", "vitality", "spirit")
    if slot:
        slots = (slot.lower(),)

    items = []
    for s in slots:
        items.extend(shop.get(s, []))

    if tier is not None:
        items = [i for i in items if i.get("tier") == tier]

    return items


@app.get("/api/items/{item_id}")
def get_item(item_id: str):
    shop_path = os.path.join(DATA_DIR, "shop.json")
    if not os.path.exists(shop_path):
        raise HTTPException(status_code=404, detail="shop.json not found")
    shop = _load_json(shop_path)

    for slot in ("weapon", "vitality", "spirit"):
        for item in shop.get(slot, []):
            if item.get("id") == item_id:
                return item

    raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")


async def stream_ask(question: str, history: list):
    from langchain_core.messages import HumanMessage
    from src.rag.rag import get_llm, build_prompt, CALC_KEYWORDS, get_route_and_context

    route, context, results = get_route_and_context(question, history, verbose=True)
    prompt = build_prompt(question, context, history)

    needs_tools = any(
        kw in question.lower() for kw in CALC_KEYWORDS
    )

    usage_data = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0
    }

    if needs_tools:
        from src.rag.rag import call_llm_with_tools
        with get_openai_callback() as cb:
            answer = call_llm_with_tools(prompt, history)
            usage_data = {
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_tokens": cb.total_tokens,
                "cost_usd": round(cb.total_cost, 6)
            }
        yield f"data: {json.dumps({'type': 'token', 'content': answer})}\n\n"
    else:
        # stream tokens via LangChain
        llm = get_llm(with_tools=False)
        full_response = ""
        with get_openai_callback() as cb:
            async for chunk in llm.astream(prompt):
                if chunk.content:
                    full_response += chunk.content
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
            
            usage_data = {
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_tokens": cb.total_tokens,
                "cost_usd": round(cb.total_cost, 6)
            }

    # sources
    sources = [
        {
            "type": r["type"],
            "name": r["metadata"].get("name") or
                    r["metadata"].get("hero") or
                    r["metadata"].get("id", ""),
            "score": round(r["score"], 4)
        }
        for r in results
    ]
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

    # yield usage BEFORE done
    yield f"data: {json.dumps({'type': 'usage', **usage_data})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@app.post("/api/ask")
async def ask_rag(request: AskRequest):
    return StreamingResponse(stream_ask(request.question, request.history), media_type="text/event-stream")



# ── Static assets ─────────────────────────────────────────────────────────────

if not os.path.exists(WEB_DIR):
    os.makedirs(WEB_DIR, exist_ok=True)

app.mount("/", StaticFiles(directory=WEB_DIR), name="static")

if __name__ == "__main__":
    # Explicitly tell uvicorn to watch the 'src' directory
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["src"])
