import json
import os
import requests
import sys

# Add the project root to sys.path to allow importing src.*
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.rag.retriever import retrieve, format_context
from src.rag.router import route_query

# Config
OLLAMA_URL = "http://localhost:11434"
LLM_MODEL  = "qwen2.5:7b"

HEROES_INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "heroes_index.json"
)

# System Prompt
SYSTEM_PROMPT = """You are an expert Deadlock game assistant.
Deadlock is a 6v6 hero shooter MOBA developed by Valve.

Your rules:
1. Answer using ONLY the provided context. Never use outside knowledge
   for specific numbers, stats, or game mechanics.
2. If the question requires math (e.g. damage at X spirit power),
   always show the formula and calculation step by step.
3. If the context does not contain enough information to answer,
   say exactly: "I don't have enough data to answer this question."
4. Be concise and precise.
5. When referencing stats, always mention the source
   (e.g. "According to Infernus's ability data...").
"""

def build_prompt(question: str, context: str,
                 history: list[dict] | None = None) -> str:
    """Combine system prompt, optional history, context, and question."""
    parts = [SYSTEM_PROMPT]

    if history:
        lines = []
        for msg in history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        parts.append("CONVERSATION HISTORY:\n" + "\n".join(lines))

    parts.append(f"CONTEXT:\n{context}")
    parts.append(f"QUESTION: {question}")
    parts.append("ANSWER:")

    return "\n\n".join(parts) + "\n"


def call_llm(prompt: str) -> str:
    """POST to Ollama /api/generate and return the response text (blocking)."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            },
            timeout=60
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")
        return response.json()["response"].strip()
    except Exception as e:
        raise RuntimeError(f"Failed to call LLM at {OLLAMA_URL}: {e}")


def call_llm_stream(prompt: str):
    """POST to Ollama /api/generate and yield tokens as they arrive."""
    import time
    try:
        _t0 = time.time()
        print(f"[DEBUG rag] calling LLM stream ({LLM_MODEL}, prompt_len={len(prompt)})...", flush=True)
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            },
            stream=True,
            timeout=(10, 120)  # (connect_timeout, read_timeout) — was 60 (connect only)
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")

        token_count = 0
        first_token_time = None
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "response" in chunk:
                    if first_token_time is None:
                        first_token_time = time.time()
                        print(f"[DEBUG rag] first token arrived in {first_token_time-_t0:.2f}s", flush=True)
                    token_count += 1
                    yield chunk["response"]
                if chunk.get("done"):
                    print(f"[DEBUG rag] LLM stream done: {token_count} tokens in {time.time()-_t0:.2f}s", flush=True)
                    break
    except Exception as e:
        raise RuntimeError(f"Failed to call LLM at {OLLAMA_URL}: {e}")


def ask(
    question: str,
    history: list[dict] | None = None,
    verbose: bool = False
) -> tuple[str, list[dict]]:
    """Main RAG pipeline. Returns (answer, sources)."""
    route, context, results = _get_route_and_context(question, history, verbose)
    prompt = build_prompt(question, context, history)
    answer = call_llm(prompt)
    return answer, results


def ask_stream(
    question: str,
    history: list[dict] | None = None,
    verbose: bool = False
):
    """Main RAG pipeline (streaming). Yields ('token', text) or ('sources', list)."""
    import time
    _t0 = time.time()
    print(f"[DEBUG rag] ask_stream started: {question!r}", flush=True)

    print(f"[DEBUG rag] step 1: routing + retrieval...", flush=True)
    route, context, results = _get_route_and_context(question, history, verbose)
    print(f"[DEBUG rag] step 1 done in {time.time()-_t0:.2f}s — {len(results)} results, route={route.get('collections')}", flush=True)

    yield "sources", results

    print(f"[DEBUG rag] step 2: building prompt...", flush=True)
    prompt = build_prompt(question, context, history)
    print(f"[DEBUG rag] step 2 done — prompt_len={len(prompt)}", flush=True)

    print(f"[DEBUG rag] step 3: streaming LLM...", flush=True)
    for token in call_llm_stream(prompt):
        yield "token", token
    print(f"[DEBUG rag] step 3 done — total {time.time()-_t0:.2f}s", flush=True)


def _get_route_and_context(question: str, history: list[dict] | None, verbose: bool):
    """Shared logic for routing and context preparation."""
    route = route_query(question)

    if verbose:
        print(f"Route: use_full_index={route['use_full_index']}, "
              f"collections={route['collections']}, "
              f"top_k={route['top_k']}, hero_filter={route['hero_filter']} "
              f"— {route.get('reasoning', '')}")

    if route.get("use_full_index"):
        with open(HEROES_INDEX_PATH, encoding="utf-8") as f:
            all_heroes = json.load(f)

        lines = []
        for h in all_heroes:
            w  = h.get("weapon", {})
            s  = h.get("base_stats", {})
            sc = h.get("scaling_per_level", {})
            lines.append(
                f"{h['name']} | {h['hero_type']} | "
                f"health: {s.get('health')} | "
                f"bullet_dmg: {w.get('bullet_damage')} | "
                f"rps: {w.get('rounds_per_sec')} | "
                f"bullet_speed: {w.get('bullet_speed')} | "
                f"spirit_power_per_lvl: {sc.get('spirit_power')}"
            )
        context = "ALL HEROES DATA:\n" + "\n".join(lines)
        results = []
    else:
        filters = {"hero": route["hero_filter"]} if route.get("hero_filter") else None
        results = retrieve(
            question,
            collections=route["collections"],
            top_k=route["top_k"],
            filters=filters,
        )

        if not results:
            context = "No results found."
        else:
            context = format_context(results)

        if verbose:
            for r in results:
                print(f"  [{r['score']:.3f}] {r['type']}: "
                      f"{r['metadata'].get('name', r['metadata'].get('hero'))}")

    return route, context, results


def main():
    """Interactive REPL for the Deadlock AI Assistant."""
    print("Deadlock AI Assistant — ask anything, 'quit' to exit")

    history: list[dict] = []
    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if question == "quit":
            break
        if not question:
            continue

        try:
            answer, sources = ask(question, history, verbose=True)
            print(f"\nAssistant: {answer}")
        except Exception as e:
            print(f"\nError: {e}")
            continue

        history.append({"role": "user",      "content": question})
        history.append({"role": "assistant", "content": answer})
        history = history[-6:]


if __name__ == "__main__":
    main()
