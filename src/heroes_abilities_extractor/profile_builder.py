from utils import normalize, get_stat_name
from classifiers import extract_hero_tags, infer_damage_type, infer_utility
from ability_extractor import extract_abilities
from weapon_extractor import extract_weapon

def extract_hero_profile(h_key, h_data, base_stats_fallback, base_scaling_fallback, loc, parsed_abilities, valid_items):
    hero = {}
    hero["hero"] = h_key
    hero["hero_id"] = normalize(h_data.get("m_HeroID", 0))
    
    disp_name = loc["hero_names"].get(h_key, h_key)
    hero["name"] = disp_name
    
    hero_type = h_data.get("m_eHeroType", "Unknown")
    hero["hero_type"] = hero_type.replace("ECitadelHeroType_", "")
    hero["complexity"] = normalize(h_data.get("m_nComplexity", 1))
    
    tags = {"flavor": [], "playstyle": [], "damage_type": [], "utility": []}
    flavor = extract_hero_tags(h_key, disp_name, loc["hero_tags_by_keyword"])
    tags["flavor"] = flavor
    
    if hero["hero_type"].lower() != "unknown":
        tags["playstyle"].append(hero["hero_type"].lower())
        
    hero["tags"] = tags # update contents later
    
    # --- Base Stats ---
    raw_stats = dict(base_stats_fallback)
    raw_stats.update(h_data.get("m_mapStartingStats", {}))
    
    clean_stats = {}
    for k, v in raw_stats.items():
        val = normalize(v)
        if isinstance(val, (int, float)):
            if "Scale" in k or k in ["EHeroSpiritLifestealEffectiveness", "EHeroBulletLifestealEffectiveness"]:
                 if val == 1.0: continue
            if "AbilityResource" in k and val == 0:
                 continue
            clean_name = get_stat_name(k, loc["stat_labels"])
            if clean_name == "max_health" or clean_name == "health": clean_name = "health"
            elif clean_name == "health_regen": clean_name = "health_regen"
            clean_stats[clean_name] = val
    hero["base_stats"] = clean_stats

    # --- Scaling ---
    raw_scaling = dict(base_scaling_fallback)
    raw_scaling.update(h_data.get("m_mapStandardLevelUpUpgrades", {}))
    clean_scaling = {}
    for k, v in raw_scaling.items():
        val = normalize(v)
        if isinstance(val, (int, float)) and val != 0:
            clean_name = get_stat_name(k, loc["stat_labels"])
            if clean_name == "base_health_from_level": clean_name = "health"
            if clean_name == "tech_power": clean_name = "spirit_power"
            clean_scaling[clean_name] = val
    hero["scaling_per_level"] = clean_scaling

    # --- Abilities ---
    bound_abs = h_data.get("m_mapBoundAbilities", {})
    hero_abilities = extract_abilities(bound_abs, parsed_abilities, loc)
    hero["abilities"] = hero_abilities

    # Playstyle inferred from effects
    tags["damage_type"].extend(infer_damage_type(hero_abilities))
    tags["utility"].extend(infer_utility(hero_abilities))
    if "Damage" in hero_type: tags["damage_type"].append("burst") # generic
    
    # Remove duplicates from tags
    for tk in tags: tags[tk] = list(set(tags[tk]))
    hero["tags"] = tags

    # --- Weapon ---
    hero["weapon"] = extract_weapon(bound_abs, parsed_abilities)

    # --- Good Items ---
    good_items = []
    # from mapItemRecommendations or mapItemDraftBucketing
    item_recs = h_data.get("m_mapItemRecommendations", h_data.get("m_mapItemDraftBucketing", {}))
    for item_key, item_val in item_recs.items():
        if item_key not in valid_items:
            continue
        if isinstance(item_val, dict):
            if item_val.get("m_strBucket") == "Good":
                good_items.append({
                    "id": item_key,
                    "name": valid_items[item_key]
                })
    hero["good_items"] = good_items
    
    return hero

def create_index_entry(hero):
    h_idx = dict(hero)
    
    # summarize abilities
    abs_summ = []
    for ab in hero.get("abilities", []):
        summ = {
            "slot": ab["slot"],
            "name": ab["name"],
            "cast_type": ab["cast_type"],
            "targeting": ab["targeting"],
            "stats": dict(ab.get("stats", {})) # flat copy
        }
        eff_types = list(set([e.get("type", "buff") for e in ab.get("effects", [])]))
        summ["effect_types"] = eff_types
        abs_summ.append(summ)
        
    h_idx["abilities"] = abs_summ
    
    # Good items is an array of objects, simplify to just IDs for index? No, prompt says: 
    # Array of all heroes. Each entry contains everything needed. "abilities summary only".
    # Keep good_items as is.
    return h_idx
