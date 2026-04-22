from utils import normalize

def extract_weapon(bound_abs: dict, parsed_abilities: dict) -> dict:
    weapon_id = bound_abs.get("ESlot_Weapon_Primary", "")
    weapon_data = parsed_abilities.get(weapon_id, {})
    weapon_props = weapon_data.get("m_WeaponInfo", {})
    
    weapon = {"id": weapon_id}
    if weapon_props:
        weapon["bullet_damage"] = normalize(weapon_props.get("m_flBulletDamage", 0))
        cycle = normalize(weapon_props.get("m_flCycleTime", 0))
        weapon["rounds_per_sec"] = normalize(round(1.0 / cycle, 2)) if cycle else 0
        weapon["clip_size"] = normalize(weapon_props.get("m_iClipSize", 0))
        weapon["reload_time"] = normalize(weapon_props.get("m_reloadDuration", 0))
        weapon["bullet_speed"] = normalize(weapon_props.get("m_flBulletSpeed", 0))
        weapon["bullets_per_shot"] = normalize(weapon_props.get("m_iBullets", 1))
        weapon["bullet_gravity"] = normalize(weapon_props.get("m_flBulletGravityScale", 0.0))
        weapon["spread"] = normalize(weapon_props.get("m_Spread", 0))
        weapon["standing_spread"] = normalize(weapon_props.get("m_StandingSpread", 0))
        weapon["inherit_shooter_velocity"] = normalize(weapon_props.get("m_flBulletInheritShooterVelocityScale", 0))
        
        falloff_start = normalize(weapon_props.get("m_flDamageFalloffStartRange", 0))
        falloff_end = normalize(weapon_props.get("m_flDamageFalloffEndRange", 0))
        weapon["falloff_range"] = [falloff_start, falloff_end]
        
        fs_start = normalize(weapon_props.get("m_flDamageFalloffStartScale", 1.0))
        fs_end = normalize(weapon_props.get("m_flDamageFalloffEndScale", 1.0))
        weapon["falloff_scale"] = [fs_start, fs_end]
        
        weapon["falloff_bias"] = normalize(weapon_props.get("m_flDamageFalloffBias", 0))
        
        crit_start = normalize(weapon_props.get("m_flCritBonusStart", 0))
        crit_end = normalize(weapon_props.get("m_flCritBonusEnd", crit_start))
        if crit_start == crit_end:
            weapon["crit_bonus"] = crit_start
        else:
            weapon["crit_bonus"] = [crit_start, crit_end]
            
        cr_start = normalize(weapon_props.get("m_flCritBonusStartRange", 0))
        cr_end = normalize(weapon_props.get("m_flCritBonusEndRange", 0))
        weapon["crit_range"] = [cr_start, cr_end]
        
        can_zoom = weapon_data.get("m_bCanZoom", "false")
        weapon["can_zoom"] = (can_zoom == "true" or can_zoom is True)
        
        attrs = []
        weapon_attrs = weapon_props.get("m_eWeaponAttributes", "")
        if isinstance(weapon_attrs, str) and weapon_attrs:
            attrs = [a.strip().replace("EWeaponAttribute_", "").lower() for a in weapon_attrs.split("|")]
        elif isinstance(weapon_attrs, list): 
            attrs = [a.replace("EWeaponAttribute_", "").lower() for a in weapon_attrs]
        
        weapon["attributes"] = [a for a in attrs if a and a != "none"]
        
    return weapon
