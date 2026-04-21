import json
import os
import requests
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add the project root to sys.path to allow importing src.*
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.config import OLLAMA_URL, LLM_MODEL
from src.rag.retriever import retrieve, format_context
from src.rag.router import route_query

CALC_KEYWORDS = {
    "how much damage", "calculate", "dps", "damage per second",
    "how many", "compare", "highest", "lowest", "most", "least",
    "how does", "scale", "at 100", "at 150", "at 200",
    "burst", "sustained", "who has", "rank"
}

HEROES_INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "heroes_index.json"
)

# System Prompt
SYSTEM_PROMPT = """You are the Shopkeeper of the Cursed Apple — 
a merchant of arcane knowledge in the world of Deadlock.

RESPONSE STYLE:
- Lead with the actual answer — facts and numbers first
- Add ONE-TWO short flavourful phrase at the start or end
- Keep character voice subtle, not overwhelming
- Never pad responses with vague mystical commentary

GOOD example:
"Mystic Shot deals 75 + (spirit_power × 0.42) damage on hit 
and applies a 30% slow. On Infernus it synergises well with 
Afterburn — the slow keeps enemies in burn range longer. 
A fine choice, friend."

BAD example (too much flavour, not enough data):
"Ah, dear seeker, the path of the arcane is fraught with peril...
[3 sentences of nothing] ...weigh the benefits against the cost."

KNOWLEDGE RULES:
- Answer ONLY from provided context
- Never invent stats not in context
- No LaTeX — use plain text: damage = 125 + (spirit_power × 0.97)
- Heroes are playable CHARACTERS, not abilities or mechanics
- If context is insufficient:
  "The archive holds no record of this, friend."
- NEVER use LaTeX notation
- NEVER reproduce raw internal IDs like hero_inferno or 
  upgrade_mystic_reach — use proper names instead"""

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


def get_llm(with_tools: bool = False):
    provider = os.getenv("LLM_PROVIDER", "ollama")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.1,
            max_tokens=1000
        )
    elif provider == "azure":
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION",
                                   "2024-02-01"),
            temperature=0.1,
            max_tokens=1000
        )
    else:  # ollama fallback
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", LLM_MODEL),
            temperature=0.1,
            num_predict=1000
        )

    if with_tools:
        try:
            from src.rag.tools import DEADLOCK_TOOLS
            return llm.bind_tools(DEADLOCK_TOOLS)
        except ImportError:
            # Fallback if tools.py is not yet created or accessible
            return llm
    return llm


def call_llm(prompt: str) -> str:
    from langchain_core.messages import HumanMessage
    llm = get_llm(with_tools=False)
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def call_llm_with_tools(prompt: str, history: list[dict] | None = None) -> str:
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from src.rag.tools import DEADLOCK_TOOLS

    history_messages = []
    for msg in (history or [])[-6:]:
        if msg["role"] == "user":
            history_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history_messages.append(AIMessage(content=msg["content"]))

    messages = history_messages + [HumanMessage(content=prompt)]

    llm_with_tools = get_llm(with_tools=True)

    print(f"[DEBUG rag] Starting tool-calling loop...", flush=True)
    for _ in range(5):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            print("[DEBUG rag] No more tool calls. LLM provided final answer.", flush=True)
            break

        for tc in response.tool_calls:
            print(f"[DEBUG rag] LLM triggered tool call: {tc['name']} with args: {tc['args']}", flush=True)
            tool_fn = next(
                (t for t in DEADLOCK_TOOLS if t.name == tc["name"]),
                None
            )
            try:
                result = tool_fn.invoke(tc["args"]) if tool_fn \
                    else json.dumps({"error": f"Unknown tool: {tc['name']}"})
            except Exception as e:
                result = json.dumps({"error": str(e)})

            print(f"[DEBUG rag] Tool {tc['name']} returned: {result}", flush=True)
            messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tc["id"]
            ))

    return response.content.strip()


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
                },
                "think": False
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
    route, context, results = get_route_and_context(question, history, verbose)
    prompt = build_prompt(question, context, history)

    needs_tools = any(kw in question.lower() for kw in CALC_KEYWORDS)
    if needs_tools:
        answer = call_llm_with_tools(prompt, history)
    else:
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
    route, context, results = get_route_and_context(question, history, verbose)
    print(f"[DEBUG rag] step 1 done in {time.time()-_t0:.2f}s — {len(results)} results, route={route.get('collections')}", flush=True)

    yield "sources", results

    print(f"[DEBUG rag] step 2: building prompt...", flush=True)
    prompt = build_prompt(question, context, history)
    print(f"[DEBUG rag] step 2 done — prompt_len={len(prompt)}", flush=True)

    print(f"[DEBUG rag] step 3: streaming LLM...", flush=True)
    for token in call_llm_stream(prompt):
        yield "token", token
    print(f"[DEBUG rag] step 3 done — total {time.time()-_t0:.2f}s", flush=True)


def get_route_and_context(question: str, history: list[dict] | None, verbose: bool):
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

        _diff_label = {1: "beginner", 2: "intermediate", 3: "advanced"}
        lines = []
        for h in all_heroes:
            w  = h.get("weapon", {})
            s  = h.get("base_stats", {})
            sc = h.get("scaling_per_level", {})
            complexity = h.get("complexity")
            diff = f"{complexity}/3 ({_diff_label.get(complexity, 'unknown')})"
            lines.append(
                f"{h['name']} | {h['hero_type']} | "
                f"difficulty: {diff} | "
                f"tags: {', '.join(h.get('tags', {}).get('playstyle', []))} | "
                f"health: {s.get('health')} | "
                f"bullet_dmg: {w.get('bullet_damage')} | "
                f"rps: {w.get('rounds_per_sec')} | "
                f"bullet_speed: {w.get('bullet_speed')} | "
                f"spirit_power_per_lvl: {sc.get('spirit_power')}"
            )
        context = "ALL HEROES DATA:\n" + "\n".join(lines)
        results = []
    else:
        collections = route["collections"]
        hero_filter = route.get("hero_filter")
        top_k = route["top_k"]

        # For build queries (items + hero_filter), retrieve hero/ability context
        # and items separately so items aren't crowded out by hero/ability chunks.
        is_build_query = (
            "item" in collections
            and hero_filter
            and len(collections) > 1
        )

        if is_build_query:
            hero_cols = [c for c in collections if c != "item"]
            hero_results = retrieve(
                question,
                collections=hero_cols,
                top_k=top_k,
                filters={"hero": hero_filter},
            )
            item_results = retrieve(
                question,
                collections=["item"],
                top_k=top_k,
            )
            results = hero_results + item_results
        else:
            filters = {"hero": hero_filter} if hero_filter else None
            results = retrieve(
                question,
                collections=collections,
                top_k=top_k,
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
