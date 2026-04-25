import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Any, Optional
import re
from src.config import WIKI_API_URL

class WikiScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "DeadlockRAGBot/1.0 (Contact: your-email@example.com)"
        }

    def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to make API requests with rate limiting."""
        params.setdefault("format", "json")
        params.setdefault("origin", "*")
        
        try:
            response = self.session.get(WIKI_API_URL, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            time.sleep(0.5)  # Respectful rate limiting
            data = response.json()
            if data is None:
                return {}
            return data
        except Exception as e:
            print(f"API Request failed for {params.get('page', 'unknown')}: {e}")
            return {}

    def fetch_category_members(self, category_name: str) -> List[str]:
        """Fetch all page titles in a given category."""
        titles = []
        cmcontinue = None
        
        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{category_name}",
                "cmlimit": "max"
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
                
            data = self._get(params)
            members = data.get("query", {}).get("categorymembers", [])
            titles.extend([m["title"] for m in members if m["ns"] == 0])  # Only main namespace
            
            cmcontinue = data.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                break
                
        return titles

    def fetch_page_content(self, title: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse page content."""
        params = {
            "action": "parse",
            "page": title,
            "prop": "text|sections"
        }
        
        data = self._get(params)
        if not data:
            return None
            
        parse_data = data.get("parse")
        if not parse_data:
            return None
            
        html_content = parse_data.get("text", {}).get("*", "")
        sections = parse_data.get("sections", [])
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove scripts, styles, and other noise
        for tag in soup(["script", "style", "table", "nav", "footer"]):
            tag.decompose()
            
        return {
            "title": title,
            "text": soup.get_text(separator="\n", strip=True),
            "html": html_content,
            "sections": sections
        }

    def _extract_section(self, title: str, sections: List[Dict[str, Any]], keywords: List[str]) -> str:
        """Extract text content of a section based on keywords."""
        target_index = None
        for s in sections:
            if any(k.lower() in s["line"].lower() for k in keywords):
                target_index = s["index"]
                break
        
        if target_index is None:
            return ""

        params = {
            "action": "parse",
            "page": title,
            "section": target_index,
            "prop": "text"
        }
        
        data = self._get(params)
        if not data:
            return ""
            
        parse_data = data.get("parse")
        if not parse_data:
            return ""
            
        html = parse_data.get("text", {}).get("*", "")
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove headers and templates
        for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            h.decompose()
        # Remove specific noise
        for tag in soup.find_all(["table", "nav", "style", "script"]):
            tag.decompose()
            
        for div in soup.find_all("div"):
            # Keep the main content div
            classes = div.attrs.get("class", []) if div.attrs else []
            if "mw-parser-output" in classes:
                continue
            # Remove typical template/navigation divs
            noise_classes = ["infobox", "navbox", "metadata", "s-videoplayer", "mw-editsection", "toc"]
            if any(c in classes for c in noise_classes):
                div.decompose()
                continue
            # If it's a small div or has specific non-content attributes, maybe remove?
            # For now, let's keep most divs to avoid losing content like blockquotes
            
        text = soup.get_text(separator="\n", strip=True)
        # Clean up [edit | edit source] with possible newlines
        text = re.sub(r'\[\s*edit\s*\|\s*edit\s+source\s*\]', '', text, flags=re.I | re.DOTALL)
        # Clean up references [1], [2], [10] with possible newlines
        text = re.sub(r'\[\s*\d+\s*\]', '', text, flags=re.DOTALL)
        # Clean up cite errors
        text = re.sub(r'Cite error:.*', '', text)
        # Remove reference lines at the bottom (starting with ↑ or numbers followed by dot)
        lines = []
        for l in text.split('\n'):
            l_strip = l.strip()
            if not l_strip: continue
            if l_strip.startswith('↑'): continue
            if re.match(r'^\d+\.\d+', l_strip): continue # e.g. 6.0
            # Also remove lines that are just single characters from botched template cleaning
            if len(l_strip) < 2 and l_strip in "[]|": continue
            lines.append(l)
        
        text = '\n'.join(lines).strip()
        # Final cleanup of multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def extract_hero_data(self, hero_name: str) -> Dict[str, Any]:
        """Extract description, lore, and strategy for a specific hero."""
        data = self.fetch_page_content(hero_name)
        if not data:
            return {}

        sections = data.get("sections", [])
        
        # 1. Description (Lead paragraph)
        description = ""
        try:
            params = {"action": "parse", "page": hero_name, "section": 0, "prop": "text"}
            lead_data = self._get(params)
            if lead_data:
                lead_parse = lead_data.get("parse")
                if lead_parse:
                    lead_html = lead_parse.get("text", {}).get("*", "")
                    lead_soup = BeautifulSoup(lead_html, "html.parser")
                    
                    # Remove specific noise
                    for tag in lead_soup.find_all(["table", "nav", "style", "script"]):
                        tag.decompose()
                    
                    for div in lead_soup.find_all("div"):
                        classes = div.attrs.get("class", []) if div.attrs else []
                        noise_classes = ["infobox", "navbox", "metadata", "s-videoplayer", "mw-editsection", "toc"]
                        if any(c in classes for c in noise_classes):
                            div.decompose()
                    
                    # Try to find the first meaningful paragraph
                    for p in lead_soup.find_all("p"):
                        text = p.get_text(separator=" ", strip=True)
                        # Clean up references and [edit] links
                        text = re.sub(r'\[\s*\d+\s*\]', '', text, flags=re.DOTALL)
                        text = re.sub(r'\[\s*edit\s*\|\s*edit\s+source\s*\]', '', text, flags=re.I | re.DOTALL)
                        if text and len(text) > 30:
                            description = text
                            break
                    
                    # Fallback if no <p> found or they are empty
                    if not description:
                        # Sometimes text is directly in the output or in other tags
                        all_text = lead_soup.get_text(separator="\n", strip=True)
                        lines = [l.strip() for l in all_text.split('\n') if l.strip()]
                        for line in lines:
                            # Clean line
                            line = re.sub(r'\[\s*\d+\s*\]', '', line, flags=re.DOTALL)
                            line = re.sub(r'\[\s*edit\s*\|\s*edit\s+source\s*\]', '', line, flags=re.I | re.DOTALL)
                            # Skip short lines or those looking like navigation
                            if len(line) > 40 and not any(k in line for k in ["Overview", "Quotes", "Sounds", "Gallery", "Update history"]):
                                description = line
                                break
        except Exception as e:
            print(f"Error extracting description for {hero_name}: {e}")
        
        # 2. Lore / Backstory
        backstory = self._extract_section(hero_name, sections, ["Backstory", "Lore", "Background"])
        
        # 3. Strategy / Playstyle
        strategy = self._extract_section(hero_name, sections, ["Strategy", "Playstyle", "Guide", "Gameplay"])
        
        return {
            "hero": hero_name,
            "description": description,
            "lore": backstory,
            "strategy": strategy
        }
