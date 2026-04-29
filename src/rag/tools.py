from langchain_core.tools import tool
import json
import glob

_heroes_cache = None
_shop_cache = None

def _load_heroes() -> dict:
    global _heroes_cache
    if _heroes_cache is None:
        _heroes_cache = {}
        for f in glob.glob("data/processed/heroes/*.json"):
            h = json.load(open(f, encoding="utf-8"))
            _heroes_cache[h["hero_id"]] = h
    return _heroes_cache

def _find_hero_by_name(name: str) -> dict | None:
    heroes = _load_heroes()
    name_lower = name.lower()
    for hero in heroes.values():
        if hero["name"].lower() == name_lower:
            return hero
    return None

def _load_shop() -> dict:
    global _shop_cache
    if _shop_cache is None:
        _shop_cache = json.load(
            open("data/processed/shop.json", encoding="utf-8")
        )
    return _shop_cache

@tool
def calculate_ability_damage(
    hero_name: str,
    ability_slot: int,
    spirit_power: float
) -> str:
    """Calculate the exact damage of a hero ability at a given
    spirit power value. Use when asked about ability damage,
    scaling, or 'how much damage at X spirit power'."""

    hero = _find_hero_by_name(hero_name)
    if not hero:
        return json.dumps({"error": f"Hero '{hero_name}' not found"})

    ability = next(
        (a for a in hero.get("abilities", [])
         if a.get("slot") == ability_slot),
        None
    )
    if not ability:
        return json.dumps({"error": f"Slot {ability_slot} not found"})

    effects_results = []
    for effect in ability.get("effects", []):
        if "formula" not in effect:
            continue
        base = effect.get("base_value", 0)
        ratio = effect.get("scales_with", {})
        if isinstance(ratio, dict):
            ratio = ratio.get("ratio")
        if ratio is not None:
            result = round(base + spirit_power * ratio, 2)
            effects_results.append({
                "type": effect.get("type", ""),
                "formula": effect["formula"],
                "result": result,
                "unit": effect.get("unit", "")
            })

    return json.dumps({
        "hero": hero["name"],
        "ability": ability.get("name", ""),
        "slot": ability_slot,
        "spirit_power_used": spirit_power,
        "effects": effects_results
    })

@tool
def calculate_hero_dps(hero_name: str) -> str:
    """Calculate burst DPS and sustained DPS for a hero's weapon.
    Use when asked about DPS, damage per second, or weapon damage."""

    hero = _find_hero_by_name(hero_name)
    if not hero:
        return json.dumps({"error": f"Hero '{hero_name}' not found"})

    w = hero.get("weapon", {})
    bd = w.get("bullet_damage", 0)
    rps = w.get("rounds_per_sec", 0)
    bps = w.get("bullets_per_shot", 1)
    clip = w.get("clip_size", 0)
    reload_t = w.get("reload_time", 1)

    burst_dps = round(bd * rps * bps, 2)
    sustained_dps = round(
        (clip * bd * bps) / (clip / rps + reload_t), 2
    ) if rps > 0 else 0

    return json.dumps({
        "hero": hero["name"],
        "bullet_damage": bd,
        "rounds_per_sec": rps,
        "bullets_per_shot": bps,
        "clip_size": clip,
        "reload_time": reload_t,
        "burst_dps": burst_dps,
        "sustained_dps": sustained_dps,
        "note": "Base values only, no weapon power items included"
    })

@tool
def compare_hero_stat(stat_name: str) -> str:
    """Rank all heroes by a specific stat.
    Use when asked 'who has the highest/lowest X',
    'which hero has the most X'.
    stat_name examples: health, bullet_damage, bullet_speed,
    rounds_per_sec, clip_size, move_speed"""

    heroes_index = json.load(
        open("data/processed/heroes_index.json", encoding="utf-8")
    )
    ranking = []
    for hero in heroes_index:
        value = hero.get("base_stats", {}).get(stat_name)
        if value is None:
            value = hero.get("weapon", {}).get(stat_name)
        if value is None:
            value = hero.get("scaling_per_level", {}).get(stat_name)
        if value is not None and isinstance(value, (int, float)):
            ranking.append({"hero": hero["name"], "value": value})

    if not ranking:
        return json.dumps({"error": f"Stat '{stat_name}' not found"})

    ranking.sort(key=lambda x: x["value"], reverse=True)
    for i, entry in enumerate(ranking):
        entry["rank"] = i + 1

    return json.dumps({
        "stat": stat_name,
        "total_heroes": len(ranking),
        "ranking": ranking
    })

@tool
def get_item_info(item_name: str) -> str:
    """Get full stats and effects of a shop item.
    Use when asked what an item does, its stats,
    or whether to buy a specific item."""

    shop = _load_shop()
    all_items = (
        shop.get("weapon", []) +
        shop.get("vitality", []) +
        shop.get("spirit", [])
    )
    item = next(
        (i for i in all_items
         if i["name"].lower() == item_name.lower()),
        None
    )
    if not item:
        return json.dumps({"error": f"Item '{item_name}' not found"})

    return json.dumps({
        "name": item["name"],
        "tier": item["tier"],
        "slot": item["slot"],
        "description": item.get("description", ""),
        "stats": item.get("stats", {}),
        "proc": item.get("proc", {}),
        "provides": item.get("synergies", {}).get("provides", []),
        "scales_with": item.get("synergies", {}).get("scales_with", []),
        "upgrades_from": item.get("upgrades_from", []),
        "upgrades_into": item.get("upgrades_into")
    })

@tool
def compare_two_heroes(hero_a: str, hero_b: str) -> str:
    """Compare all base stats, weapon stats, and scaling between two heroes.
    Use when asked to compare, versus, or contrast two specific heroes by name or hero_id."""

    index = json.load(open("data/processed/heroes_index.json", encoding="utf-8"))

    def find(name_or_id: str) -> dict | None:
        key = name_or_id.lower().strip()
        for h in index:
            if (h["name"].lower() == key
                    or h["hero"] == key
                    or h["hero"].replace("hero_", "") == key):
                return h
        return None

    a = find(hero_a)
    b = find(hero_b)

    if not a:
        return json.dumps({"error": f"Hero '{hero_a}' not found"})
    if not b:
        return json.dumps({"error": f"Hero '{hero_b}' not found"})

    def diff_section(key_a: dict, key_b: dict) -> dict:
        all_keys = sorted(set(key_a.keys()) | set(key_b.keys()))
        out = {}
        for k in all_keys:
            va, vb = key_a.get(k), key_b.get(k)
            if not isinstance(va, (int, float)) and not isinstance(vb, (int, float)):
                continue
            entry: dict = {a["name"]: va, b["name"]: vb}
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                entry["advantage"] = a["name"] if va > vb else (b["name"] if vb > va else "tie")
            out[k] = entry
        return out

    return json.dumps({
        "comparison": f"{a['name']} vs {b['name']}",
        "hero_type": {a["name"]: a["hero_type"], b["name"]: b["hero_type"]},
        "complexity": {a["name"]: a.get("complexity"), b["name"]: b.get("complexity")},
        "base_stats": diff_section(a.get("base_stats", {}), b.get("base_stats", {})),
        "scaling_per_level": diff_section(a.get("scaling_per_level", {}), b.get("scaling_per_level", {})),
        "weapon": diff_section(a.get("weapon", {}), b.get("weapon", {})),
    }, indent=2)


DEADLOCK_TOOLS = [
    calculate_ability_damage,
    calculate_hero_dps,
    compare_hero_stat,
    compare_two_heroes,
    get_item_info,
]
