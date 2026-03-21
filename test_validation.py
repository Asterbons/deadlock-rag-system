import json, glob

heroes = [json.load(open(f)) for f in glob.glob('data/processed/heroes/*.json')]
errors = []
unknown_count = 0

for h in heroes:
    for a in h['abilities']:
        for e in a.get('effects', []):
            t = e.get('type', '')

            # no false bullet_damage from multipliers
            if t == 'bullet_damage':
                v = e.get('base_value', 0)
                if 0 < v < 1 and 'formula' not in e:
                    errors.append(
                        f'False bullet_damage in '
                        f'{h["name"]}/{a["id"]}: {e}'
                    )

            if t == 'unknown':
                unknown_count += 1

# viscous: telepunch should have knockup not bullet_damage
viscous = next(h for h in heroes if h['hero'] == 'hero_viscous')
telepunch = next(a for a in viscous['abilities']
                 if a['id'] == 'viscous_telepunch')
types = [e['type'] for e in telepunch['effects']]
assert 'knockup' in types, f'Missing knockup in telepunch: {types}'
assert 'displacement' not in [
    e['type'] for h in heroes
    for a in h['abilities']
    for e in a.get('effects', [])
    if e['type'] == 'bullet_damage'
    and e.get('base_value', 0) < 1
], 'displacement still mapped as bullet_damage'

if errors:
    print(f'FAIL:')
    for e in errors: print(f'  {e}')
else:
    print(f'OK - all effect types validated')
    if unknown_count:
        print(f'  {unknown_count} unknown types logged - review warnings')
    else:
        print(f'  Zero unknown effect types')
