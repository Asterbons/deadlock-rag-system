"""
Ability Enricher — Merges extracted hero profiles with their ability data.

Handles:
  - Looking up signature abilities in parsed `abilities.vdata`
  - Extracting base values and scaling functions from `m_mapAbilityProperties`
"""

def enrich_hero_abilities(hero: dict, parsed_abilities: dict) -> dict:
    """Take a hero dict and enrich its signature_abilities with full ability data."""
    enriched_hero = hero.copy()
    raw_signatures = hero.get("signature_abilities", {})
    
    enriched_abilities = {}
    
    for slot, ability_name in raw_signatures.items():
        ability_data = parsed_abilities.get(ability_name)
        if not ability_data:
            # Ability not found in abilities.vdata
            enriched_abilities[slot] = {
                "ability_name": ability_name,
                "error": "Not found in abilities.vdata"
            }
            continue
            
        props = ability_data.get("m_mapAbilityProperties", {})
        
        base_values = {}
        scaling = {}
        tags_raw = set()
        
        for prop_name, prop_data in props.items():
            if not isinstance(prop_data, dict):
                continue
                
            # Extract main base value
            val = prop_data.get("m_strValue")
            if val is not None:
                base_values[prop_name] = val
                
            # Extract scaling if present
            scale_func = prop_data.get("m_subclassScaleFunction")
            if isinstance(scale_func, dict):
                scale_class = scale_func.get("_class")
                if scale_class:
                    scaling[prop_name] = {
                        "class": scale_class,
                        "scale": scale_func.get("m_flStatScale"),
                        "stat_type": scale_func.get("m_eSpecificStatScaleType")
                    }
                    if scale_class == "scale_function_tech_damage":
                        tags_raw.add("[Spirit]")
                        
            # CSS Class is useful for semantics
            css = prop_data.get("m_strCSSClass")
            if css:
                if css == "tech_damage":
                    tags_raw.add("[Spirit]")
                    
        # Apply semantic tags based on keys
        tags = list(tags_raw)
        
        # [DoT] tag logic
        is_dot = False
        for k in props.keys():
            k_lower = k.lower()
            if any(term in k_lower for term in ("burn_damage", "burn_duration", "dot", "dps", "tickrate")):
                is_dot = True
                break
        if is_dot:
            tags.append("[DoT]")
            
        # [Mobility] tag logic
        is_mobility = False
        aname_str = ability_name.lower()
        if "dash" in aname_str or "jump" in aname_str.lower() or "leap" in aname_str or "charge" in aname_str:
            is_mobility = True
        else:
            for k in props.keys():
                k_lower = k.lower()
                if "dash" in k_lower or "jump" in k_lower or "air_dash" in k_lower:
                    is_mobility = True
                    break
        if is_mobility:
            tags.append("[Mobility]")
            
        enriched_abilities[slot] = {
            "ability_name": ability_name,
            "base_values": base_values,
            "scaling": scaling,
            "tags": tags
        }
        
    enriched_hero["enriched_abilities"] = enriched_abilities
    # Keep the original signature mapping but we could optionally remove it
    return enriched_hero
