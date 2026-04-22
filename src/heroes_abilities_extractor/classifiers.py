def extract_hero_tags(internal_key, display_name, hero_tags_by_keyword):
    short_key = internal_key.replace("hero_", "").lower()
    disp_lower = display_name.lower()
    for tk, tags in hero_tags_by_keyword.items():
        if tk == short_key or tk in disp_lower:
            return tags
    return []

def infer_damage_type(hero_abilities):
    dtypes = set()
    for a in hero_abilities:
        for e in a.get("effects", []):
            if e.get("type") in ["spirit_damage", "dot"]:
                dtypes.add("spirit")
            elif e.get("type") == "bullet_damage":
                dtypes.add("bullet")
            if e.get("type") == "dot":
                dtypes.add("dot")
    return list(dtypes)

def infer_utility(hero_abilities):
    utils = set()
    for a in hero_abilities:
        for e in a.get("effects", []):
            t = e.get("type")
            if t in ["slow", "stun", "silence", "heal", "buff", "debuff"]:
                if t == "buff" or t == "debuff":
                     # might need more granular, let's keep it simple
                     pass
                else:
                     utils.add(t)
        # Also check tags if any mobility
        if a.get("targeting") == "self" and ("dash" in a.get("name", "").lower() or "jump" in a.get("name", "").lower()):
            utils.add("mobility")
    return list(utils)
