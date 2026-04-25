import json
import os
import requests
import time
from typing import List, Dict
from src.config import HEROES_INDEX_PATH, PROCESSED_DATA_DIR, WIKI_API_URL

WIKI_IMAGES_PATH = PROCESSED_DATA_DIR / "wiki_images.json"
SHOP_PATH = PROCESSED_DATA_DIR / "shop.json"
PROCESSED_HEROES_PATH = PROCESSED_DATA_DIR / "processed_heroes.json"

def chunk_list(lst: List, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def fetch_image_urls(titles: List[str]) -> Dict[str, str]:
    """Fetch image URLs from MediaWiki API for a list of File: titles."""
    results = {}
    session = requests.Session()
    headers = {"User-Agent": "DeadlockRAGBot/1.0"}
    
    # MediaWiki API accepts max 50 titles per request
    for chunk in chunk_list(titles, 50):
        params = {
            "action": "query",
            "prop": "imageinfo",
            "iiprop": "url",
            "titles": "|".join(chunk),
            "format": "json"
        }
        
        try:
            response = session.get(WIKI_API_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if int(page_id) < 0:
                    # File not found
                    continue
                title = page_data.get("title", "")
                imageinfo = page_data.get("imageinfo", [])
                if imageinfo and "url" in imageinfo[0]:
                    results[title] = imageinfo[0]["url"]
            
            time.sleep(0.5) # rate limit
        except Exception as e:
            print(f"Error fetching image chunk: {e}")
            
    return results

def run_image_pipeline():
    print("Gathering entities for image scraping...")
    entities = {} # Mapping from wiki File title -> our internal ID
    
    # 1 & 2. Heroes and Abilities
    with open(PROCESSED_HEROES_PATH, "r", encoding="utf-8") as f:
        processed_heroes = json.load(f)
        
        # processed_heroes is an object like {"hero_atlas": {...}} or an array?
        # Wait, if processed_heroes is a list... wait, no, it's a dict!
        if isinstance(processed_heroes, list):
            hero_list = processed_heroes
        else:
            hero_list = processed_heroes.values()
            
        for hero in hero_list:
            wiki_name = hero['name']
            hero_internal_id = hero['hero'] # e.g. 'hero_inferno'
            
            entities[f"File:{wiki_name}.png".replace('_', ' ')] = hero_internal_id
            entities[f"File:{wiki_name}_icon.png".replace('_', ' ')] = f"{hero_internal_id}_fallback"
            
            # Abilities
            for ab in hero.get("abilities", []):
                ab_name = ab["name"]
                wiki_file = f"File:{ab_name}.png"
                entities[wiki_file.replace('_', ' ')] = ab["id"]

    # 3. Items
    with open(SHOP_PATH, "r", encoding="utf-8") as f:
        shop = json.load(f)
        for category in ["weapon", "vitality", "spirit"]:
            if category in shop:
                for item in shop[category]:
                    item_name = item["name"]
                    wiki_file = f"File:{item_name}.png"
                    entities[wiki_file.replace('_', ' ')] = item['id']
            
    print(f"Found {len(entities)} potential images to fetch.")
    
    # Fetch URLs
    titles = list(entities.keys())
    wiki_urls = fetch_image_urls(titles)
    
    print(f"Successfully resolved {len(wiki_urls)} image URLs.")
    
    # Map back to our internal IDs
    final_images = {}
    for title, url in wiki_urls.items():
        internal_id = entities[title]
        # Ignore fallbacks if we already got the main one
        if internal_id.endswith("_fallback"):
            main_id = internal_id.replace("_fallback", "")
            if main_id not in final_images:
                final_images[main_id] = url
        else:
            final_images[internal_id] = url
            
    # Save to JSON
    os.makedirs(os.path.dirname(WIKI_IMAGES_PATH), exist_ok=True)
    with open(WIKI_IMAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(final_images, f, indent=2)
        
    print(f"Image URLs saved to {WIKI_IMAGES_PATH}")
    
    # Inject images into existing JSON files
    inject_images(final_images)

def inject_images(images: Dict[str, str]):
    print("Injecting image URLs into data files...")
    
    # 1. Update processed_heroes.json
    with open(PROCESSED_HEROES_PATH, "r", encoding="utf-8") as f:
        processed_heroes = json.load(f)
        
    for hero_id, hero_data in processed_heroes.items() if isinstance(processed_heroes, dict) else enumerate(processed_heroes):
        hero = hero_data if isinstance(processed_heroes, dict) else hero_data
        
        # Inject hero image
        if hero['hero'] in images:
            hero['image'] = images[hero['hero']]
            
        # Inject ability images
        for ab in hero.get("abilities", []):
            if ab['id'] in images:
                ab['image'] = images[ab['id']]
                
    with open(PROCESSED_HEROES_PATH, "w", encoding="utf-8") as f:
        json.dump(processed_heroes, f, indent=2)
        
    # 2. Update heroes_index.json
    with open(HEROES_INDEX_PATH, "r", encoding="utf-8") as f:
        heroes = json.load(f)
        
    for hero in heroes:
        hero_internal_id = f"hero_{hero['name'].lower()}" # Approximate, better to check images keys
        # We can find hero internal id by checking processed_heroes matching name
        # Actually, in heroes_index.json we have `hero` field which is internal id!
        if "hero" in hero and hero["hero"] in images:
            hero["image"] = images[hero["hero"]]
            
    with open(HEROES_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(heroes, f, indent=2)
        
    # 3. Update shop.json
    with open(SHOP_PATH, "r", encoding="utf-8") as f:
        shop = json.load(f)
        
    for category in ["weapon", "vitality", "spirit"]:
        if category in shop:
            for item in shop[category]:
                if item['id'] in images:
                    item['image'] = images[item['id']]
                    
    with open(SHOP_PATH, "w", encoding="utf-8") as f:
        json.dump(shop, f, indent=2)
        
    print("Image injection complete.")

if __name__ == "__main__":
    run_image_pipeline()
