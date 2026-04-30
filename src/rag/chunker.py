import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import HEROES_INDEX_PATH, HEROES_OUT_DIR, SHOP_JSON_PATH, CHUNKS_JSON_PATH, WIKI_DATA_PATH

logger = logging.getLogger(__name__)

def round_floats(val):
    if isinstance(val, float):
        if val.is_integer():
            return int(val)
        return round(val, 2)
    return val

def clean_dict(d):
    """Recursively clean dict from nulls, empty lists, empty dicts."""
    if not isinstance(d, dict):
        return d
    cleaned = {}
    for k, v in d.items():
        if v is None or v == [] or v == {}:
            continue
        cleaned[k] = v
    return cleaned

def format_list(lst):
    return ", ".join(str(x) for x in lst)

_ABILITY_SKIP_STATS = {
    "ability_unit_target_limit",
    "ability_cooldown_between_charge",
    "channel_move_speed",
}


def _load_hero_details(heroes_dir):
    """Load every hero detail file in `heroes_dir`, indexed by hero_id."""
    hero_details = {}
    for fname in os.listdir(heroes_dir):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(heroes_dir, fname), 'r', encoding='utf-8') as f:
                d = json.load(f)
                hero_details[d['hero_id']] = d
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Skipping hero detail file %s: %s", fname, e)
    return hero_details


def _build_stats_chunk(h):
    """Build the per-hero stats chunk (always emitted)."""
    base_stats = h.get('base_stats', {})
    weapon = h.get('weapon', {})
    scaling = h.get('scaling_per_level', {})

    stats_parts = [
        f"{h['name']} | {h.get('hero_type')} | complexity {h.get('complexity')}",
        f"health: {round_floats(base_stats.get('health'))}",
        f"move_speed: {round_floats(base_stats.get('max_move_speed'))}",
        f"bullet_damage: {round_floats(weapon.get('bullet_damage'))}",
        f"bullet_speed: {round_floats(weapon.get('bullet_speed'))}",
        f"rounds_per_sec: {round_floats(weapon.get('rounds_per_sec'))}",
        f"clip_size: {round_floats(weapon.get('clip_size'))}",
        f"can_zoom: {weapon.get('can_zoom')}",
        f"scaling: health +{round_floats(scaling.get('health'))}/lvl, spirit_power +{round_floats(scaling.get('spirit_power'))}/lvl",
    ]

    metadata = {
        "type": "hero",
        "hero": h.get("hero"),
        "hero_id": h.get("hero_id"),
        "name": h.get("name"),
        "complexity": h.get("complexity"),
        "hero_type": h.get("hero_type"),
    }
    if "image" in h:
        metadata["image"] = h["image"]

    return {
        "text": " | ".join([p for p in stats_parts if p]),
        "metadata": clean_dict(metadata),
    }


def _build_build_chunk(h):
    """Build the playstyle/recommended-items chunk. Returns None when no good_items are configured."""
    good_items_list = [item['name'] for item in h.get('good_items', [])]
    good_items_str = ", ".join(good_items_list)
    if not good_items_str:
        return None

    tags = h.get('tags', {})
    build_parts = [
        f"{h['name']} build guide | {h.get('hero_type')}",
        f"damage type: {format_list(tags.get('damage_type', []))}" if tags.get('damage_type') else "",
        f"utility: {format_list(tags.get('utility', []))}" if tags.get('utility') else "",
        f"playstyle: {format_list(tags.get('playstyle', []))}" if tags.get('playstyle') else "",
        f"flavor tags: {format_list(tags.get('flavor', []))}" if tags.get('flavor') else "",
        f"good items: {good_items_str}",
    ]

    metadata = {
        "type": "hero_build",
        "hero": h.get("hero"),
        "hero_id": h.get("hero_id"),
        "name": h.get("name"),
        "hero_type": h.get("hero_type"),
    }
    if "image" in h:
        metadata["image"] = h["image"]

    return {
        "text": " | ".join([p for p in build_parts if p]),
        "metadata": clean_dict(metadata),
    }


def _format_ability_effects(effects):
    """Render an ability's effects list to display strings."""
    out = []
    for e in effects:
        etype = e.get('type', '')
        formula = e.get('formula')
        base_value = e.get('base_value', 0)
        unit = e.get('unit', '')
        # Skip zero-value effects with no formula (belt-and-suspenders)
        if not formula and base_value == 0:
            continue
        if formula:
            out.append(f"{etype}: {formula}")
        else:
            value_str = f"{round_floats(base_value)}{unit}" if unit == '%' else f"{round_floats(base_value)} {unit}"
            out.append(f"{etype}: {value_str.strip()}")
    return out


def _build_ability_chunks(h, details):
    """Build per-ability chunks for one hero. Returns [] when details is None or has no abilities."""
    if not details:
        return []

    chunks = []
    for ability in details.get('abilities', []):
        ab_parts = [
            f"{h['name']} | {ability.get('name')} | slot {ability.get('slot')} | {ability.get('cast_type')} | {ability.get('targeting')}"
        ]
        if ability.get('description'):
            ab_parts.append(ability.get('description'))

        stats_clean = {}
        for k, v in ability.get('stats', {}).items():
            if k in _ABILITY_SKIP_STATS:
                continue
            if v is None or v == [] or v == {}:
                continue
            stats_clean[k] = round_floats(v)
        if stats_clean:
            stats_str = json.dumps(stats_clean).replace('"', "'")
            ab_parts.append(f"stats: {stats_str}")

        effects = ability.get('effects', [])
        effect_strings = _format_ability_effects(effects)
        if effect_strings:
            ab_parts.append(f"effects: {', '.join(effect_strings)}")

        upgrades = ability.get('upgrades', [])
        upg_desc = [u.get('description') for u in upgrades if u.get('description')]
        if upg_desc:
            ab_parts.append(f"upgrades: {format_list(upg_desc)}")

        ab_metadata = {
            "type": "ability",
            "hero": h.get("hero"),
            "hero_id": h.get("hero_id"),
            "hero_name": h.get("name"),
            "ability_id": ability.get("id"),
            "slot": ability.get("slot"),
            "cast_type": ability.get("cast_type"),
        }
        # Ability-specific image first, then fall back to the hero portrait
        image = ability.get("image") or h.get("image")
        if image:
            ab_metadata["image"] = image

        matching_ab_index = next((x for x in h.get('abilities', []) if x.get('slot') == ability.get('slot')), None)
        if matching_ab_index and matching_ab_index.get('effect_types'):
            ab_metadata['effect_types'] = matching_ab_index['effect_types']
        else:
            eff_types = list(set([e.get('type') for e in effects if e.get('type')]))
            if eff_types:
                ab_metadata['effect_types'] = eff_types

        chunks.append({
            "text": " | ".join(ab_parts),
            "metadata": clean_dict(ab_metadata),
        })

    return chunks


def chunk_heroes(index_path, heroes_dir):
    with open(index_path, 'r', encoding='utf-8') as f:
        heroes_index = json.load(f)

    hero_details = _load_hero_details(heroes_dir)

    chunks = []
    for h in heroes_index:
        chunks.append(_build_stats_chunk(h))

        build_chunk = _build_build_chunk(h)
        if build_chunk is not None:
            chunks.append(build_chunk)

        chunks.extend(_build_ability_chunks(h, hero_details.get(h.get('hero_id'))))

    return chunks

def chunk_items(shop_path):
    with open(shop_path, 'r', encoding='utf-8') as f:
        shop = json.load(f)
        
    chunks = []
    
    # Build a lookup map for item names to resolve upgrades
    item_lookup = {}
    for cat in ["weapon", "vitality", "spirit"]:
        if cat in shop:
            for item in shop[cat]:
                item_lookup[item['id']] = item['name']

    for category in ["weapon", "vitality", "spirit"]:
        if category not in shop:
            continue
        for item in shop[category]:
            text_parts = []
            
            text_parts.append(f"{item.get('name')} | tier {item.get('tier')} | {item.get('slot')}")
            
            passive = item.get('passive')
            if passive is not None:
                text_parts.append("passive" if passive else "active")

            if item.get('description'):
                text_parts.append(item.get('description'))
            
            if item.get('passive_description'):
                text_parts.append(f"passive: {item['passive_description']}")
                
            stats_clean = {}
            for k, v in item.get('stats', {}).items():
                if v is None or v == [] or v == {}:
                    continue
                stats_clean[k] = round_floats(v)
            if stats_clean:
                stats_str = json.dumps(stats_clean).replace('"', "'")
                text_parts.append(f"stats: {stats_str}")
                
            proc = item.get('proc', {})
            
            # Proc basic info
            if proc.get('trigger'):
                text_parts.append(f"trigger: {proc['trigger']}")
            
            proc_chance = proc.get('proc_chance_pct')
            if proc_chance and proc_chance < 100:
                text_parts.append(f"proc_chance: {round_floats(proc_chance)}%")

            # Proc effects
            effects = proc.get('effects', [])
            eff_desc = [e.get('description') for e in effects if e.get('description')]
            if eff_desc:
                text_parts.append(f"effects: {format_list(eff_desc)}")
                
            # Proc parameters
            for field in ['radius', 'duration_sec', 'move_slow_pct', 'conditions']:
                val = proc.get(field)
                if val:
                    label = field.replace('_sec', 's').replace('_pct', '%').replace('_', ' ')
                    # Use underscore for some labels to match user script expectations if needed
                    if field == 'move_slow_pct': label = 'slow'
                    text_parts.append(f"{label}: {round_floats(val)}")

            cooldown = proc.get('cooldown_sec')
            if cooldown is None:
                cooldown = proc.get('item_cooldown_sec')
            if cooldown is None:
                cooldown = proc.get('proc_cooldown_sec')
            if cooldown is not None:
                text_parts.append(f"proc cooldown: {round_floats(cooldown)}s")

            # Components
            components = item.get('component_items', [])
            if components:
                text_parts.append(f"components: {format_list(components)}")
                
            synergies = item.get('synergies', {})
            scales_with = synergies.get('scales_with', [])
            if scales_with:
                text_parts.append(f"scales_with: {format_list(scales_with)}")
                
            provides = synergies.get('provides', [])
            if provides:
                text_parts.append(f"provides: {format_list(provides)}")
                
            # Upgrade chains
            upgrades_from = item.get('upgrades_from', [])
            if upgrades_from:
                from_names = [item_lookup.get(cid, cid) for cid in upgrades_from]
                text_parts.append(f"upgrades from: {', '.join(from_names)}")
            
            upgrades_into = item.get('upgrades_into')
            if upgrades_into:
                into_name = item_lookup.get(upgrades_into, upgrades_into)
                text_parts.append(f"upgrades into: {into_name}")

            upgrade = item.get('upgrade')
            if upgrade:
                text_parts.append(f"upgrade: {upgrade}")
                
            item_text = " | ".join(text_parts)
            
            if len(item_text) <= 50:
                continue
                
            metadata = {
                "type": "item",
                "item_id": item.get('id'),
                "name": item.get('name'),
                "tier": item.get('tier'),
                "slot": item.get('slot')
            }
            if "image" in item:
                metadata["image"] = item["image"]
            
            chunks.append({
                "text": item_text,
                "metadata": clean_dict(metadata)
            })
            
    return chunks

def chunk_wiki(wiki_path):
    if not os.path.exists(wiki_path):
        return []
        
    with open(wiki_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Load heroes index for name -> id mapping
    with open(HEROES_INDEX_PATH, 'r', encoding='utf-8') as f:
        heroes_index = json.load(f)
    name_to_id = {h['name']: h['hero'] for h in heroes_index}
        
    chunks = []
    
    # 1. Hero Wiki Data
    for hero_name, hero_data in data.get("heroes", {}).items():
        hero_id = name_to_id.get(hero_name)
        
        # Hero Description (First Guide)
        if hero_data.get("description"):
            chunks.append({
                "text": f"{hero_name} Overview: {hero_data['description']}",
                "metadata": {
                    "type": "wiki_guide",
                    "hero": hero_id,
                    "hero_name": hero_name,
                    "category": "hero_description"
                }
            })
            
        # Hero Lore
        if hero_data.get("lore"):
            chunks.append({
                "text": f"{hero_name} Lore / Backstory:\n{hero_data['lore']}",
                "metadata": {
                    "type": "wiki_lore",
                    "hero": hero_id,
                    "hero_name": hero_name,
                    "category": "hero_lore"
                }
            })
            
        # Hero Strategy
        if hero_data.get("strategy"):
            chunks.append({
                "text": f"{hero_name} Strategy / Playstyle:\n{hero_data['strategy']}",
                "metadata": {
                    "type": "wiki_guide",
                    "hero": hero_id,
                    "hero_name": hero_name,
                    "category": "hero_strategy"
                }
            })
            
    # 2. General Lore
    for lore_page in data.get("lore", []):
        chunks.append({
            "text": f"Lore: {lore_page['title']}\n{lore_page['content']}",
            "metadata": {
                "type": "wiki_lore",
                "title": lore_page['title'],
                "category": "general_lore"
            }
        })
        
    # 3. General Guides/Mechanics
    for guide_page in data.get("guides", []):
        chunks.append({
            "text": f"Mechanics/Guide: {guide_page['title']}\n{guide_page['content']}",
            "metadata": {
                "type": "wiki_guide",
                "title": guide_page['title'],
                "category": "general_mechanics"
            }
        })
        
    return chunks

def build_all_chunks():
    chunks = chunk_heroes(HEROES_INDEX_PATH, HEROES_OUT_DIR)
    chunks += chunk_items(SHOP_JSON_PATH)
    chunks += chunk_wiki(WIKI_DATA_PATH)
    return chunks

if __name__ == "__main__":
    chunks = build_all_chunks()
    with open(CHUNKS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2)
    print(f"Generated {len(chunks)} chunks, saved to {CHUNKS_JSON_PATH}")
