import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import HEROES_INDEX_PATH, HEROES_OUT_DIR, SHOP_JSON_PATH, CHUNKS_JSON_PATH

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

def chunk_heroes(index_path, heroes_dir):
    with open(index_path, 'r', encoding='utf-8') as f:
        heroes_index = json.load(f)
        
    chunks = []
    
    # Pre-load abilities from heroes_dir
    hero_details = {}
    for fname in os.listdir(heroes_dir):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(heroes_dir, fname), 'r', encoding='utf-8') as f:
                d = json.load(f)
                hero_details[d['hero_id']] = d
        except Exception:
            pass
            
    for h in heroes_index:
        # 1. Hero chunk
        good_items_list = [item['name'] for item in h.get('good_items', [])]
        good_items_str = ", ".join(good_items_list)
        
        tags = h.get('tags', {})
        base_stats = h.get('base_stats', {})
        weapon = h.get('weapon', {})
        scaling = h.get('scaling_per_level', {})
        
        text_parts = [
            f"{h['name']} | {h.get('hero_type')} | complexity {h.get('complexity')}",
            f"flavor tags: {format_list(tags.get('flavor', []))}" if tags.get('flavor') else "",
            f"damage: {format_list(tags.get('damage_type', []))}" if tags.get('damage_type') else "",
            f"utility: {format_list(tags.get('utility', []))}" if tags.get('utility') else "",
            f"playstyle: {format_list(tags.get('playstyle', []))}" if tags.get('playstyle') else "",
            f"health: {round_floats(base_stats.get('health'))}",
            f"move_speed: {round_floats(base_stats.get('max_move_speed'))}",
            f"bullet_damage: {round_floats(weapon.get('bullet_damage'))}",
            f"bullet_speed: {round_floats(weapon.get('bullet_speed'))}",
            f"rounds_per_sec: {round_floats(weapon.get('rounds_per_sec'))}",
            f"clip_size: {round_floats(weapon.get('clip_size'))}",
            f"can_zoom: {weapon.get('can_zoom')}",
            f"scaling: health +{round_floats(scaling.get('health'))}/lvl, spirit_power +{round_floats(scaling.get('spirit_power'))}/lvl"
        ]
        
        if good_items_str:
            text_parts.append(f"good items: {good_items_str}")
            
        hero_text = " | ".join([p for p in text_parts if p])
        
        metadata = {
            "type": "hero",
            "hero": h.get("hero"),
            "hero_id": h.get("hero_id"),
            "name": h.get("name"),
            "complexity": h.get("complexity"),
            "hero_type": h.get("hero_type")
        }
        
        chunks.append({
            "text": hero_text,
            "metadata": clean_dict(metadata)
        })
        
        # 2. Ability chunk
        details = hero_details.get(h.get('hero_id'))
        if details:
            for ability in details.get('abilities', []):
                ab_parts = [
                    f"{h['name']} | {ability.get('name')} | slot {ability.get('slot')} | {ability.get('cast_type')} | {ability.get('targeting')}"
                ]
                if ability.get('description'):
                    ab_parts.append(ability.get('description'))
                    
                skip_stats = {"ability_unit_target_limit", "ability_cooldown_between_charge", "channel_move_speed"}
                stats_clean = {}
                for k, v in ability.get('stats', {}).items():
                    if k in skip_stats:
                        continue
                    if v is None or v == [] or v == {}:
                        continue
                    stats_clean[k] = round_floats(v)
                if stats_clean:
                    stats_str = json.dumps(stats_clean).replace('"', "'")
                    ab_parts.append(f"stats: {stats_str}")
                    
                effects = ability.get('effects', [])
                effect_strings = []
                for e in effects:
                    etype = e.get('type', '')
                    formula = e.get('formula')
                    base_value = e.get('base_value', 0)
                    unit = e.get('unit', '')
                    # Skip zero-value effects with no formula (belt-and-suspenders)
                    if not formula and base_value == 0:
                        continue
                    if formula:
                        effect_strings.append(f"{etype}: {formula}")
                    else:
                        value_str = f"{round_floats(base_value)}{unit}" if unit == '%' else f"{round_floats(base_value)} {unit}"
                        effect_strings.append(f"{etype}: {value_str.strip()}")
                if effect_strings:
                    ab_parts.append(f"effects: {', '.join(effect_strings)}")
                    
                upgrades = ability.get('upgrades', [])
                upg_desc = [u.get('description') for u in upgrades if u.get('description')]
                if upg_desc:
                    ab_parts.append(f"upgrades: {format_list(upg_desc)}")
                    
                ab_text = " | ".join(ab_parts)
                
                ab_metadata = {
                    "type": "ability",
                    "hero": h.get("hero"),
                    "hero_id": h.get("hero_id"),
                    "hero_name": h.get("name"),
                    "ability_id": ability.get("id"),
                    "slot": ability.get("slot"),
                    "cast_type": ability.get("cast_type")
                }
                
                matching_ab_index = next((x for x in h.get('abilities', []) if x.get('slot') == ability.get('slot')), None)
                if matching_ab_index and matching_ab_index.get('effect_types'):
                    ab_metadata['effect_types'] = matching_ab_index['effect_types']
                else:
                    eff_types = list(set([e.get('type') for e in effects if e.get('type')]))
                    if eff_types:
                        ab_metadata['effect_types'] = eff_types
                
                chunks.append({
                    "text": ab_text,
                    "metadata": clean_dict(ab_metadata)
                })
                
    return chunks

def chunk_items(shop_path):
    with open(shop_path, 'r', encoding='utf-8') as f:
        shop = json.load(f)
        
    chunks = []
    
    for category in ["weapon", "vitality", "spirit"]:
        if category not in shop:
            continue
        for item in shop[category]:
            text_parts = []
            
            text_parts.append(f"{item.get('name')} | tier {item.get('tier')} | {item.get('slot')}")
            
            if item.get('description'):
                text_parts.append(item.get('description'))
                
            stats_clean = {}
            for k, v in item.get('stats', {}).items():
                if v is None or v == [] or v == {}:
                    continue
                stats_clean[k] = round_floats(v)
            if stats_clean:
                stats_str = json.dumps(stats_clean).replace('"', "'")
                text_parts.append(f"stats: {stats_str}")
                
            proc = item.get('proc', {})
            effects = proc.get('effects', [])
            eff_desc = [e.get('description') for e in effects if e.get('description')]
            if eff_desc:
                text_parts.append(f"effects: {format_list(eff_desc)}")
                
            cooldown = proc.get('cooldown_sec')
            if cooldown is None:
                cooldown = proc.get('item_cooldown_sec')
            if cooldown is None:
                cooldown = proc.get('proc_cooldown_sec')
            if cooldown is not None:
                text_parts.append(f"proc cooldown: {round_floats(cooldown)}s")
                
            synergies = item.get('synergies', {})
            scales_with = synergies.get('scales_with', [])
            if scales_with:
                text_parts.append(f"scales_with: {format_list(scales_with)}")
                
            provides = synergies.get('provides', [])
            if provides:
                text_parts.append(f"provides: {format_list(provides)}")
                
            upgrade = item.get('upgrade')
            if upgrade:
                text_parts.append(f"upgrade: {upgrade}")
                
            item_text = " | ".join(text_parts)
            
            if len(item_text) <= 50:
                continue
                
            metadata = {
                "type": "item",
                "id": item.get("id"),
                "name": item.get("name"),
                "slot": item.get("slot"),
                "tier": item.get("tier")
            }
            
            chunks.append({
                "text": item_text,
                "metadata": clean_dict(metadata)
            })
            
    return chunks

def build_all_chunks():
    chunks = chunk_heroes(HEROES_INDEX_PATH, HEROES_OUT_DIR)
    chunks += chunk_items(SHOP_JSON_PATH)
    return chunks

if __name__ == "__main__":
    chunks = build_all_chunks()
    with open(CHUNKS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2)
    print(f"Generated {len(chunks)} chunks, saved to {CHUNKS_JSON_PATH}")
