
import json
data = json.load(open('data/processed/processed_heroes.json', encoding='utf-8'))
for hero in data.values():
    if not isinstance(hero, dict) or 'abilities' not in hero: continue
    for ab in hero['abilities']:
        if ab['id'] in ['ability_werewolf_kickflip', 'ability_necro_gravestone']:
            print(ab['name'], ':', ab['description'])

