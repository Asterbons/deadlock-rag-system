import json, re

shop = json.load(open('data/processed/shop.json'))
all_items = shop['weapon'] + shop['vitality'] + shop['spirit']
item_by_id = {i['id']: i for i in all_items}

errors = []
text = json.dumps(shop)

# Bug 1: no double underscores anywhere
if '__' in text:
    # find which fields
    for item in all_items:
        t = json.dumps(item)
        if '__' in t:
            errors.append(f'Double underscore in {item["id"]}: {t[:100]}')

# Bug 2: no template items
template_pattern = re.compile(r'.+_upgrade_t[1-5]$')
for item in all_items:
    if template_pattern.match(item['id']):
        errors.append(f'Template item leaked: {item["id"]}')
    if item.get('name') in ['T1', 'T2', 'T3', 'T4', 'T5']:
        errors.append(f'Unnamed template: {item["id"]}')

# Bonus: baseattack_damage_percent cleaned up
if 'baseattack_damage_percent' in text:
    errors.append('baseattack_damage_percent not normalized')

# Spot check crackshot
cs = item_by_id.get('upgrade_crackshot')
if cs is None:
    errors.append('upgrade_crackshot not found')
else:
    synergies_str = json.dumps(cs.get('synergies', {}))
    if 'spirit_power' not in synergies_str:
         errors.append('spirit_power missing from crackshot synergies')
    if '__' in json.dumps(cs):
        errors.append('Double underscore in crackshot')

if errors:
    print(f'FAIL - {len(errors)} errors:')
    for e in errors: print(f'  {e}')
else:
    total = len(all_items)
    print(f'OK - {total} items, no double underscores, no templates')
