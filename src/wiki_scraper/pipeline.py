import json
import os
from src.wiki_scraper.scraper import WikiScraper
from src.config import HEROES_INDEX_PATH, WIKI_DATA_PATH

def run_pipeline():
    scraper = WikiScraper()
    
    # 1. Load heroes
    with open(HEROES_INDEX_PATH, "r") as f:
        heroes = json.load(f)
    
    wiki_data = {
        "heroes": {},
        "lore": [],
        "guides": []
    }
    
    # 2. Scrape Hero Data
    print(f"Scraping data for {len(heroes)} heroes...")
    for hero in heroes:
        hero_name = hero["name"]
        print(f"  Scraping {hero_name}...")
        hero_wiki = scraper.extract_hero_data(hero_name)
        if hero_wiki:
            wiki_data["heroes"][hero_name] = hero_wiki
            
    # 3. Scrape Category:Lore
    print("Scraping Lore category...")
    lore_titles = scraper.fetch_category_members("Lore")
    for title in lore_titles:
        if "/" in title: continue # Skip subpages (translations)
        if title in wiki_data["heroes"]: continue # Skip hero pages as they are handled
        try:
            print(f"  Scraping lore page: {title}...")
        except UnicodeEncodeError:
            print(f"  Scraping lore page: [Unicode Title]...")
        page_data = scraper.fetch_page_content(title)
        if page_data:
            wiki_data["lore"].append({
                "title": title,
                "content": page_data["text"]
            })
            
    # 4. Scrape Category:Gameplay / Mechanics
    print("Scraping Gameplay category...")
    gameplay_titles = scraper.fetch_category_members("Gameplay")
    for title in gameplay_titles:
        if "/" in title: continue
        try:
            print(f"  Scraping gameplay page: {title}...")
        except UnicodeEncodeError:
            print(f"  Scraping gameplay page: [Unicode Title]...")
        page_data = scraper.fetch_page_content(title)
        if page_data:
            wiki_data["guides"].append({
                "title": title,
                "content": page_data["text"]
            })
            
    # 5. Save results
    os.makedirs(os.path.dirname(WIKI_DATA_PATH), exist_ok=True)
    with open(WIKI_DATA_PATH, "w") as f:
        json.dump(wiki_data, f, indent=2)
    
    print(f"Wiki data saved to {WIKI_DATA_PATH}")

if __name__ == "__main__":
    run_pipeline()
