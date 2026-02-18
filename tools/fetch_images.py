#!/usr/bin/env python3
"""
Fragrantica Image Pipeline v2
==============================
Instead of searching for each product individually (triggers rate limits),
this script scrapes Fragrantica BRAND PAGES to build a local lookup table,
then matches products using fuzzy string matching and downloads images
directly from the CDN (which is not rate-limited).

Phase 1: Scrape ~250 brand pages → local catalog of {name → image_id}
Phase 2: Fuzzy-match our products against the catalog
Phase 3: Download images from fimgs.net CDN

Usage:
    python3 tools/fetch_images.py [--max-brands N] [--reset] [--dry-run]
"""

import asyncio
import json
import os
import re
import sys
import time
import random
import hashlib
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

try:
    from playwright.async_api import async_playwright, Page
    from playwright_stealth import stealth_async
except ImportError:
    print("ERROR: playwright and playwright-stealth are required.")
    print("  pip3 install playwright tf-playwright-stealth")
    sys.exit(1)

try:
    from PIL import Image
    import io
except ImportError:
    print("ERROR: Pillow is required. Install with: pip3 install Pillow")
    sys.exit(1)

try:
    import httpx
except ImportError:
    httpx = None
    import requests


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "public" / "images" / "products"
PRODUCTS_FILE = DATA_DIR / "products.json"
CATALOG_FILE = DATA_DIR / "fragrantica_catalog.json"  # scraped brand data
CHECKPOINT_FILE = DATA_DIR / "image_checkpoint.json"

# Config
MAX_IMAGE_WIDTH = 400
MAX_IMAGE_HEIGHT = 500
WEBP_QUALITY = 85
BRAND_PAGE_DELAY = 4.0  # seconds between brand page requests
FUZZY_THRESHOLD = 0.55  # minimum similarity score for matching


# ─── Brand name mapping: our brands → Fragrantica URL slugs ───
# Many "brands" in our data are actually product lines (e.g., "Boss" = Hugo Boss,
# "Good Girl" = Carolina Herrera). This map normalizes them.
BRAND_URL_MAP = {
    # Actual brands
    "Abercrombie": "Abercrombie---Fitch", "Abercrombie & Fitch": "Abercrombie---Fitch",
    "Acqua di Parma": "Acqua-di-Parma",
    "Adidas": "Adidas", "Afnan": "Afnan", "Ajmal": "Ajmal",
    "Al Haramain": "Al-Haramain-Perfumes",
    "Amouage": "Amouage", "Animale": "Animale",
    "Antonio Banderas": "Antonio-Banderas",
    "Aramis": "Aramis", "Armaf": "Armaf", "Azzaro": "Azzaro",
    "Balmain": "Balmain", "Bebe": "Bebe",
    "Benetton": "Benetton", "Bentley": "Bentley",
    "Bond No.9": "Bond-No-9", "Bond No. 9": "Bond-No-9",
    "Boucheron": "Boucheron",
    "Britney Spears": "Britney-Spears",
    "Bulgari": "Bvlgari", "Bvlgari": "Bvlgari",
    "Burberry": "Burberry",
    "Calvin Klein": "Calvin-Klein",
    "Carolina Herrera": "Carolina-Herrera",
    "Cartier": "Cartier", "Chanel": "Chanel",
    "Chloe": "Chloe",
    "Clive Christian": "Clive-Christian",
    "Coach": "Coach", "Creed": "Creed",
    "Cuba": "Cuba-Paris",
    "D&G": "Dolce-Gabbana", "Dior": "Dior",
    "Diesel": "Diesel", "Diptyque": "Diptyque",
    "DKNY": "DKNY",
    "Dolce & Gabbana": "Dolce-Gabbana",
    "Donna Karan": "Donna-Karan",
    "Ed Hardy": "Ed-Hardy",
    "Elizabeth Arden": "Elizabeth-Arden",
    "Elizabeth Taylor": "Elizabeth-Taylor",
    "Escada": "Escada",
    "Estee Lauder": "Estee-Lauder",
    "Ferragamo": "Salvatore-Ferragamo", "Salvatore Ferragamo": "Salvatore-Ferragamo",
    "Ferrari": "Ferrari",
    "Fugazzi": "Fugazzi",
    "Givenchy": "Givenchy",
    "Gucci": "Gucci", "Guess": "Guess", "Guerlain": "Guerlain",
    "Halston": "Halston",
    "Hugo Boss": "Hugo-Boss",
    "Initio": "Initio-Parfums-Prives",
    "Issey Miyake": "Issey-Miyake",
    "Jaguar": "Jaguar",
    "Jean Paul Gaultier": "Jean-Paul-Gaultier",
    "Jimmy Choo": "Jimmy-Choo",
    "Jo Malone": "Jo-Malone-London",
    "John Varvatos": "John-Varvatos",
    "Joop": "JOOP-",
    "Juicy Couture": "Juicy-Couture",
    "Kenneth Cole": "Kenneth-Cole",
    "Kenzo": "Kenzo",
    "Kilian": "By-Kilian",
    "La Rive": "La-Rive",
    "Lacoste": "Lacoste", "Lalique": "Lalique",
    "Lancome": "Lancome",
    "Lattafa": "Lattafa",
    "Loewe": "Loewe",
    "Lomani": "Lomani",
    "Mancera": "Mancera",
    "Marc Jacobs": "Marc-Jacobs",
    "Maison Francis Kurkdjian": "Maison-Francis-Kurkdjian",
    "Mercedes Benz": "Mercedes-Benz", "Mercedes-Benz": "Mercedes-Benz",
    "Michael Kors": "Michael-Kors",
    "Missoni": "Missoni",
    "Montale": "Montale",
    "Mont Blanc": "Montblanc", "Montblanc": "Montblanc",
    "Moschino": "Moschino",
    "Mugler": "Mugler",
    "Narciso Rodriguez": "Narciso-Rodriguez",
    "Nautica": "Nautica", "Nishane": "Nishane",
    "Oscar de la Renta": "Oscar-de-la-Renta",
    "Paco Rabanne": "Paco-Rabanne",
    "Parfums de Marly": "Parfums-de-Marly",
    "Paris Hilton": "Paris-Hilton",
    "Penhaligons": "Penhaligon-s", "Penhaligon's": "Penhaligon-s",
    "Penguin": "Original-Penguin",
    "Perry Ellis": "Perry-Ellis",
    "Prada": "Prada",
    "Ralph Lauren": "Ralph-Lauren",
    "Rochas": "Rochas",
    "Roja": "Roja-Dove",
    "Sean John": "Sean-John",
    "Shakira": "Shakira",
    "Swiss Army": "Victorinox-Swiss-Army",
    "Tiziana": "Tiziana-Terenzi",
    "Tom Ford": "Tom-Ford",
    "Tommy Bahama": "Tommy-Bahama",
    "Tommy Hilfiger": "Tommy-Hilfiger",
    "Tous": "Tous",
    "Valentino": "Valentino",
    "Van Cleef & Arpels": "Van-Cleef-Arpels",
    "Vera Wang": "Vera-Wang",
    "Versace": "Versace",
    "Viktor & Rolf": "Viktor-Rolf",
    "Vince Camuto": "Vince-Camuto",
    "Xerjoff": "Xerjoff",
    "YSL": "Yves-Saint-Laurent", "Yves Saint Laurent": "Yves-Saint-Laurent",
    "Zara": "Zara",
    # Product-line "brands" → actual parent brand on Fragrantica
    "1 Million": "Paco-Rabanne", "1 Million Elixir": "Paco-Rabanne",
    "1 Million Elixir Intense": "Paco-Rabanne", "1 Million Golden Oud": "Paco-Rabanne",
    "1 Million Gold Intense": "Paco-Rabanne", "1 Million Lucky": "Paco-Rabanne",
    "1 Million Prive": "Paco-Rabanne",
    "212": "Carolina-Herrera", "212 Heroes": "Carolina-Herrera", "212 VIP": "Carolina-Herrera",
    "Acqua": "Giorgio-Armani", "Acqua Di Gio": "Giorgio-Armani",
    "Armani": "Giorgio-Armani",
    "Bad Boy": "Carolina-Herrera",
    "Boss": "Hugo-Boss", "Hugo": "Hugo-Boss",
    "Cabotine": "Gres",
    "CH": "Carolina-Herrera",
    "CK": "Calvin-Klein",
    "Chrome": "Azzaro",
    "Club de Nuit": "Armaf",
    "Cool Water": "Davidoff",
    "Curve": "Liz-Claiborne",
    "Daisy": "Marc-Jacobs",
    "Declaration": "Cartier",
    "Dolce": "Dolce-Gabbana", "Dylan": "Versace",
    "Eros": "Versace",
    "Eternity": "Calvin-Klein", "Euphoria": "Calvin-Klein",
    "Flowerbomb": "Viktor-Rolf",
    "Good Girl": "Carolina-Herrera",
    "Halloween": "Jesus-Del-Pozo",
    "Her": "Burberry",
    "Idole": "Lancome",
    "Incanto": "Salvatore-Ferragamo",
    "Invictus": "Paco-Rabanne",
    "Jimmy": "Jimmy-Choo",
    "King": "Dolce-Gabbana",
    "La Vie Est Belle": "Lancome",
    "Lady": "Dior", "Le Male": "Jean-Paul-Gaultier",
    "Legend": "Montblanc",
    "Light Blue": "Dolce-Gabbana",
    "L'Homme": "Yves-Saint-Laurent",
    "Miss Dior": "Dior",
    "Narciso": "Narciso-Rodriguez",
    "Odyssey": "Armaf",
    "Olympea": "Paco-Rabanne",
    "Omnia": "Bvlgari",
    "One": "Calvin-Klein",
    "Pasha": "Cartier",
    "Phantom": "Paco-Rabanne",
    "Polo": "Ralph-Lauren", "Private": "Ralph-Lauren",
    "Replica": "Maison-Martin-Margiela",
    "Rose": "Valentino",
    "Sauvage": "Dior",
    "Scandal": "Jean-Paul-Gaultier",
    "Signorina": "Salvatore-Ferragamo",
    "Spicebomb": "Viktor-Rolf",
    "Supremacy": "Afnan",
    "Sweet": "Lolita-Lempicka",
    "The": "Dolce-Gabbana",  # "The One" etc.
    "Tommy": "Tommy-Hilfiger",
    "Tresor": "Lancome",
    "Velvet": "Dolce-Gabbana",
    "Viva La Juicy": "Juicy-Couture",
    "360": "Perry-Ellis", "360 Collection": "Perry-Ellis",
    "Alien": "Mugler", "Angel": "Mugler",
    "5th": "Elizabeth-Arden",
    "Bharara": "Bharara",
    "Blue Seduction": "Antonio-Banderas",
    "Mr.": "Burberry",
    "Territoire": "YZY-Perfume",
    "AB Spirit Millionaire": "Lomani",
    "Perry": "Perry-Ellis",
    "Arsenal": "Gilles-Cantuel",
    "Black": "Bvlgari",
    "Eau": "Rochas",
    "Jean": "Jean-Paul-Gaultier",
    "Jo": "Jo-Malone-London",
    "Le": "Jean-Paul-Gaultier",
    "Live": "Lacoste",
    "My": "Burberry",
    "Royal": "Creed",
    # Additional niche brands
    "Orientica": "Orientica", "Emper": "Emper",
    "Daniel Josier": "Daniel-Josier",
    "Insurrection": "Reyane-Tradition",
    "Zimaya": "Zimaya", "Bharara": "Bharara",
    "Ainash": "Ainash",
    "La": "Yves-Saint-Laurent",  # "La Nuit de l'Homme" etc.
    "Night": "Yves-Saint-Laurent",  # "La Nuit" etc.
    "Pure": "Paco-Rabanne",  # "Pure XS" etc.
    "Very": "Versace",  # "Versace Pour Homme" etc.
    "Love": "Chloe",  # "Love, Chloe" etc.
    "Red": "Lacoste",  # "Lacoste Red" etc.
    "United": "Benetton",  # "United Colors of Benetton"
    "Game": "Davidoff",
    "Genius": "Armaf",
    "Amber": "Prada",
    "Art": "Diptyque",
    "Bella": "Vince-Camuto",
    "Pink": "Lacoste",
    "White": "Lacoste",
    "R2B2": "Reyane-Tradition",
    "So": "Loewe",
    "Big": "Carolina-Herrera",
    "New": "Calvin-Klein",
    "Only": "Calvin-Klein",
    "Real": "Nike",
    "Acqua di Parisis": "Reyane-Tradition",
    "Ilmin Il": "Ilmin",
    "AHLI": "Bait-Al-Bakhoor",
}


def clean_name_for_matching(name: str) -> str:
    """Normalize a product name for fuzzy matching."""
    n = name.lower()
    # Remove common noise words
    for word in ['eau de', 'pour homme', 'pour femme', 'for men', 'for women',
                 'for him', 'for her', 'parfum', 'spray', 'edp', 'edt', 'edc']:
        n = n.replace(word, '')
    n = re.sub(r'\d+\.?\d*\s*oz', '', n)
    n = re.sub(r'\b(tester|refillable|gift set)\b', '', n, flags=re.IGNORECASE)
    n = re.sub(r'[^a-z0-9\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def clean_search_query(raw_name: str) -> str:
    """Extract a clean fragrance name for grouping."""
    q = raw_name
    q = re.sub(r'\d+\.?\d*\s*oz\.?', '', q)
    for t in ['EDP', 'EDT', 'EDC', 'Parfum', 'Cologne', 'Body Mist', 'Body Spray']:
        q = re.sub(r'\b' + re.escape(t) + r'\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\bfor\s+(men|women|woman|unisex)\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\bTESTER\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\bGift\s+Set\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\bRe\s*f+il+able\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\b\d+\s*(Piece|PC|Pcs?)\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\b[a-z]?\d{10,}\b', '', q)
    q = re.sub(r'\b\d+\.\d+$', '', q)
    q = re.sub(r'\s+', ' ', q).strip().strip('.')
    return q


def make_image_filename(query: str) -> str:
    """Generate a stable filename from search query."""
    slug = re.sub(r'[^a-z0-9]+', '-', query.lower()).strip('-')
    h = hashlib.md5(query.encode()).hexdigest()[:6]
    return f"{slug[:80]}-{h}.webp"


def get_our_brands(products: list) -> Dict[str, str]:
    """Get unique brand names from our products and map to Fragrantica URLs.
    Only returns brands with explicit mappings."""
    brands = set(p['brand'] for p in products)
    return {b: BRAND_URL_MAP[b] for b in brands if b in BRAND_URL_MAP}


async def scrape_brand_page(page: Page, brand_slug: str) -> List[dict]:
    """Scrape a Fragrantica brand/designer page for all product entries."""
    url = f"https://www.fragrantica.com/designers/{brand_slug}.html"

    try:
        resp = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
        await page.wait_for_timeout(1500)

        # Check for errors
        content = await page.content()
        if 'too many requests' in content.lower() or 'giphy.com' in content.lower():
            return "RATE_LIMITED"

        if resp and resp.status == 404:
            return []

        # Extract all perfume entries
        entries = []
        links = await page.query_selector_all('a[href*="/perfume/"]')

        for link in links:
            href = await link.get_attribute('href') or ''
            if '/perfume/' not in href or not href.endswith('.html'):
                continue

            # Extract product ID from URL
            id_match = re.search(r'-(\d+)\.html$', href)
            if not id_match:
                continue

            frag_id = id_match.group(1)
            text = (await link.inner_text()).strip()

            # Extract product name (first line of text)
            name = text.split('\n')[0].strip()

            # Check for image
            img = await link.query_selector('img')
            has_img = img is not None

            if name and frag_id:
                entries.append({
                    "name": name,
                    "id": frag_id,
                    "url": href if href.startswith('http') else f"https://www.fragrantica.com{href}",
                    "has_img": has_img,
                })

        return entries

    except Exception as e:
        print(f"    [!] Error: {e}")
        return []


async def download_image(url: str) -> Optional[bytes]:
    """Download an image from the CDN (not rate-limited)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.fragrantica.com/',
    }
    try:
        if httpx:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 500:
                    return resp.content
        else:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 500:
                return resp.content
    except Exception:
        pass
    return None


def process_image(image_data: bytes, output_path: Path) -> bool:
    """Resize image and save as WebP."""
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.mode in ('RGBA', 'P', 'LA'):
            bg = Image.new('RGB', img.size, (10, 10, 10))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)
        img.save(str(output_path), 'WEBP', quality=WEBP_QUALITY)
        return True
    except Exception as e:
        print(f"    [!] Image processing error: {e}")
        return False


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"completed": {}, "failed": [], "stats": {"searched": 0, "downloaded": 0}}


def save_checkpoint(checkpoint: dict):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)


def match_products_to_catalog(products: list, catalog: dict) -> Dict[str, dict]:
    """
    Match our products to Fragrantica catalog entries using fuzzy matching.
    Returns: {clean_query -> {image_file, fragrantica_url}}
    """
    matches = {}
    unmatched = 0

    # Build lookup: brand → list of (clean_name, entry)
    brand_lookup = {}
    for brand_slug, entries in catalog.items():
        for entry in entries:
            clean = clean_name_for_matching(entry['name'])
            if brand_slug not in brand_lookup:
                brand_lookup[brand_slug] = []
            brand_lookup[brand_slug].append((clean, entry))

    # Group our products
    groups = defaultdict(list)
    for p in products:
        if p.get('is_gift_set'):
            continue
        query = clean_search_query(p['raw_name'])
        if len(query) >= 3:
            groups[query].append(p)

    brand_map = get_our_brands(products)

    for query, prods in groups.items():
        brand = prods[0]['brand']
        slug = brand_map.get(brand, '')

        # Get the Fragrantica entries for this brand
        entries = brand_lookup.get(slug, [])
        if not entries:
            # Try without brand prefix in query
            unmatched += 1
            continue

        # Clean our product name for matching
        our_clean = clean_name_for_matching(query)

        # Find best match
        best_score = 0
        best_entry = None

        for their_clean, entry in entries:
            # SequenceMatcher ratio
            score = SequenceMatcher(None, our_clean, their_clean).ratio()

            # Boost if key words match
            our_words = set(our_clean.split())
            their_words = set(their_clean.split())
            overlap = len(our_words & their_words)
            if our_words and their_words:
                word_score = overlap / max(len(our_words), len(their_words))
                score = score * 0.6 + word_score * 0.4

            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry and best_score >= FUZZY_THRESHOLD:
            filename = make_image_filename(query)
            matches[query] = {
                "frag_id": best_entry['id'],
                "frag_name": best_entry['name'],
                "frag_url": best_entry['url'],
                "image_url": f"https://fimgs.net/mdimg/perfume-thumbs/375x500.{best_entry['id']}.jpg",
                "image_file": f"/images/products/{filename}",
                "score": round(best_score, 3),
            }
        else:
            unmatched += 1

    print(f"Matched: {len(matches)} | Unmatched: {unmatched}")
    return matches


async def phase1_scrape_brands(page: Page, products: list, max_brands: Optional[int] = None) -> dict:
    """Phase 1: Scrape Fragrantica brand pages to build local catalog."""

    # Load existing catalog if any
    catalog = {}
    if CATALOG_FILE.exists():
        with open(CATALOG_FILE) as f:
            catalog = json.load(f)
        print(f"Loaded existing catalog: {len(catalog)} brands, "
              f"{sum(len(v) for v in catalog.values())} products")

    brand_map = get_our_brands(products)
    # Deduplicate slugs (many brands map to the same Fragrantica designer)
    slugs_needed = set(brand_map.values())
    slugs_todo = [s for s in slugs_needed if s not in catalog]

    if max_brands:
        slugs_todo = slugs_todo[:max_brands]

    print(f"Brand slugs: {len(slugs_needed)} total, {len(slugs_todo)} to scrape")

    if not slugs_todo:
        print("All brands already scraped!")
        return catalog

    for i, slug in enumerate(slugs_todo):
        print(f"[{i+1}/{len(slugs_todo)}] Scraping: {slug}")

        entries = await scrape_brand_page(page, slug)

        if entries == "RATE_LIMITED":
            print("    [!] Rate limited! Waiting 5 minutes...")
            await asyncio.sleep(300)
            entries = await scrape_brand_page(page, slug)
            if entries == "RATE_LIMITED":
                print("    [!] Still limited. Saving and stopping.")
                break

        if isinstance(entries, list):
            catalog[slug] = entries
            print(f"    Found {len(entries)} products")
        else:
            catalog[slug] = []

        # Save every 10 brands
        if (i + 1) % 10 == 0:
            with open(CATALOG_FILE, 'w') as f:
                json.dump(catalog, f, indent=2)

        await asyncio.sleep(BRAND_PAGE_DELAY + random.uniform(0, 2))

    # Final save
    with open(CATALOG_FILE, 'w') as f:
        json.dump(catalog, f, indent=2)

    total_entries = sum(len(v) for v in catalog.values())
    print(f"\nCatalog complete: {len(catalog)} brands, {total_entries} products")
    return catalog


async def phase3_download_images(matches: dict, checkpoint: dict):
    """Phase 3: Download images from CDN (not rate-limited, can go fast)."""
    completed = checkpoint["completed"]
    stats = checkpoint["stats"]

    todo = {q: info for q, info in matches.items() if q not in completed}
    print(f"\nDownloading {len(todo)} images from CDN...")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    failed = 0

    for i, (query, info) in enumerate(todo.items()):
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(todo)}] {downloaded} downloaded...")

        image_data = await download_image(info["image_url"])

        if not image_data:
            failed += 1
            continue

        filename = make_image_filename(query)
        output_path = IMAGES_DIR / filename

        if process_image(image_data, output_path):
            completed[query] = {
                "image_file": info["image_file"],
                "fragrantica_url": info["frag_url"],
            }
            downloaded += 1
            stats["downloaded"] = stats.get("downloaded", 0) + 1
        else:
            failed += 1

        # Save checkpoint every 100
        if (i + 1) % 100 == 0:
            save_checkpoint(checkpoint)

        # Small delay to be polite to CDN
        await asyncio.sleep(0.1)

    save_checkpoint(checkpoint)
    print(f"Downloaded: {downloaded} | Failed: {failed}")


def update_products_json(products: list, completed: dict):
    """Update products.json with image paths."""
    for p in products:
        query = clean_search_query(p['raw_name'])
        if query in completed:
            p['image_url'] = completed[query]['image_file']
            p['has_image'] = True

    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f, indent=2)

    total = sum(1 for p in products if p.get('has_image'))
    print(f"products.json: {total}/{len(products)} have images ({total/len(products)*100:.1f}%)")


async def run_pipeline(max_brands: Optional[int] = None, dry_run: bool = False):
    with open(PRODUCTS_FILE) as f:
        products = json.load(f)
    print(f"Loaded {len(products)} products")

    checkpoint = load_checkpoint()

    if dry_run:
        brand_map = get_our_brands(products)
        slugs = set(brand_map.values())
        print(f"Would scrape {len(slugs)} brand pages on Fragrantica")
        return

    # Phase 1: Scrape brand pages
    print(f"\n{'='*60}")
    print("PHASE 1: Scraping Fragrantica brand pages")
    print(f"{'='*60}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        await stealth_async(page)

        catalog = await phase1_scrape_brands(page, products, max_brands)
        await browser.close()

    # Phase 2: Match products to catalog
    print(f"\n{'='*60}")
    print("PHASE 2: Matching products to Fragrantica catalog")
    print(f"{'='*60}\n")

    matches = match_products_to_catalog(products, catalog)

    # Phase 3: Download images from CDN
    print(f"\n{'='*60}")
    print("PHASE 3: Downloading images from CDN")
    print(f"{'='*60}")

    await phase3_download_images(matches, checkpoint)

    # Update products.json
    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}\n")
    update_products_json(products, checkpoint["completed"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch fragrance images from Fragrantica")
    parser.add_argument("--max-brands", type=int, default=None, help="Max brands to scrape")
    parser.add_argument("--reset", action="store_true", help="Clear all checkpoints")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    if args.reset:
        for f in [CHECKPOINT_FILE, CATALOG_FILE]:
            if f.exists():
                os.remove(f)
        print("Checkpoints cleared.")

    asyncio.run(run_pipeline(max_brands=args.max_brands, dry_run=args.dry_run))
