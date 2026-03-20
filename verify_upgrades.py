import json
import sys

def verify():
    try:
        with open('data/processed/shop.json', 'r', encoding='utf-8') as f:
            shop = json.load(f)
    except FileNotFoundError:
        print("FAIL - shop.json not found")
        return

    all_items = shop['weapon'] + shop['vitality'] + shop['spirit']
    item_by_id = {i['id']: i for i in all_items}
    errors = []

    for item in all_items:
        if 'upgrades_from' not in item:
            errors.append(f"Missing upgrades_from on {item['id']}")
        if 'upgrades_into' not in item:
            errors.append(f"Missing upgrades_into on {item['id']}")
        
        for cid in item.get('upgrades_from', []):
            if cid not in item_by_id:
                errors.append(f"{item['id']}: component {cid} not in shop")
        
        uid = item.get('upgrades_into')
        if uid:
            upgraded = item_by_id.get(uid)
            if not upgraded:
                errors.append(f"{item['id']}: upgrades_into {uid} not in shop")
            elif item['id'] not in upgraded.get('upgrades_from', []):
                errors.append(f"Broken reciprocal: {item['id']} -> {uid}")

    rapid = item_by_id.get('upgrade_rapid_rounds')
    blitz = item_by_id.get('upgrade_blitz_bullets')
    if rapid and blitz:
        if rapid['upgrades_into'] != 'upgrade_blitz_bullets':
            errors.append(f"Rapid Rounds upgrades_into mismatch: {rapid['upgrades_into']}")
        if 'upgrade_rapid_rounds' not in blitz['upgrades_from']:
            errors.append(f"Blitz Bullets upgrades_from mismatch: {blitz['upgrades_from']}")
    else:
        if not rapid: print("Warning: upgrade_rapid_rounds not found")
        if not blitz: print("Warning: upgrade_blitz_bullets not found")

    if errors:
        print(f"FAIL - {len(errors)} errors:")
        for e in errors:
            print(f"  {e}")
    else:
        print(f"OK - upgrade chains verified across {len(all_items)} items")

if __name__ == '__main__':
    verify()
