#!/usr/bin/env python3
"""
Fragrantica Image Pipeline
==========================
Searches Fragrantica for product images using Playwright (headless browser),
downloads bottle images, converts to WebP, and updates products.json.

Features:
- Resumable: saves progress to a checkpoint file
- Rate-limited: 1.5-2s between requests to be respectful
- Groups products by fragrance to minimize searches
- Skips gift sets (no standard product images)
- Concurrent browser pages for speed (configurable)

Usage:
    python3 tools/fetch_images.py [--max N] [--reset] [--dry-run]

Options:
    --max N     Process at most N fragrances (for testing)
    --reset     Clear checkpoint and start fresh
    --dry-run   Show what would be searched without downloading
"""

import asyncio
import json
import os
import re
import sys
import time
import hashlib
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
except ImportError:
    print("ERROR: playwright is required. Install with: pip3 install playwright")
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
    # Fallback to requests
    httpx = None
    import requests


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "public" / "images" / "products"
PRODUCTS_FILE = DATA_DIR / "products.json"
CHECKPOINT_FILE = DATA_DIR / "image_checkpoint.json"

# Config
MAX_IMAGE_WIDTH = 400
MAX_IMAGE_HEIGHT = 500
WEBP_QUALITY = 85
DELAY_BETWEEN_SEARCHES = 1.5  # seconds
SEARCH_TIMEOUT = 12000  # ms
PAGE_TIMEOUT = 10000  # ms


def clean_search_query(raw_name: str) -> str:
    """Extract a clean fragrance name for searching Fragrantica."""
    q = raw_name
    # Remove size (e.g., "3.4 oz")
    q = re.sub(r'\d+\.?\d*\s*oz\.?', '', q)
    # Remove common fragrance types
    for t in ['EDP', 'EDT', 'EDC', 'Parfum', 'Cologne', 'Body Mist', 'Body Spray',
              'Eau De Parfum', 'Eau De Toilette']:
        q = re.sub(r'\b' + re.escape(t) + r'\b', '', q, flags=re.IGNORECASE)
    # Remove gender markers
    q = re.sub(r'\bfor\s+(men|women|woman|unisex)\b', '', q, flags=re.IGNORECASE)
    # Remove TESTER, Gift Set, Refillable
    q = re.sub(r'\bTESTER\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\bGift\s+Set\b', '', q, flags=re.IGNORECASE)
    q = re.sub(r'\bRe\s*f+il+able\b', '', q, flags=re.IGNORECASE)
    # Remove piece counts (e.g., "2 Piece", "3 PC")
    q = re.sub(r'\b\d+\s*(Piece|PC|Pcs?)\b', '', q, flags=re.IGNORECASE)
    # Remove UPC artifacts (long numbers)
    q = re.sub(r'\b[a-z]?\d{10,}\b', '', q)
    # Remove trailing price artifacts (e.g., "102.0")
    q = re.sub(r'\b\d+\.\d+$', '', q)
    # Clean up whitespace and punctuation
    q = re.sub(r'\s+', ' ', q).strip().strip('.')
    return q


def group_products(products: List[dict]) -> Dict[str, List[dict]]:
    """Group products by clean fragrance name for shared image lookup."""
    groups = defaultdict(list)
    for p in products:
        if p.get('is_gift_set'):
            continue  # Skip gift sets
        query = clean_search_query(p['raw_name'])
        if len(query) < 3:
            continue  # Skip too-short queries
        groups[query].append(p)
    return dict(groups)


def make_image_filename(query: str) -> str:
    """Generate a stable filename from search query."""
    slug = re.sub(r'[^a-z0-9]+', '-', query.lower()).strip('-')
    # Add hash for uniqueness if slug is too generic
    h = hashlib.md5(query.encode()).hexdigest()[:6]
    return f"{slug[:80]}-{h}.webp"


async def search_fragrantica(page: Page, query: str) -> Optional[str]:
    """Search Fragrantica and return the first product page URL."""
    search_url = f"https://www.fragrantica.com/search/?query={query.replace(' ', '+')}"

    try:
        await page.goto(search_url, wait_until='domcontentloaded', timeout=SEARCH_TIMEOUT)
        await page.wait_for_timeout(1500)

        # Find product links in search results
        links = await page.query_selector_all('a[href*="/perfume/"]')

        for link in links[:5]:  # Check first 5 results
            href = await link.get_attribute('href')
            if href and '/perfume/' in href and href.endswith('.html'):
                # Ensure it's a full URL
                if href.startswith('/'):
                    href = 'https://www.fragrantica.com' + href
                return href

    except Exception as e:
        pass  # Will return None

    return None


async def get_product_image_url(page: Page, product_url: str) -> Optional[str]:
    """Visit a Fragrantica product page and extract the main bottle image URL."""
    try:
        await page.goto(product_url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT)
        await page.wait_for_timeout(800)

        # Primary: itemprop="image" (most reliable)
        img = await page.query_selector('img[itemprop="image"]')
        if img:
            src = await img.get_attribute('src')
            if src and 'perfume-thumbs' in src:
                # Upgrade to larger size if possible
                src = re.sub(r'/\d+x\d+\.', '/375x500.', src)
                return src

        # Fallback: look for perfume-thumbs image
        imgs = await page.query_selector_all('img[src*="perfume-thumbs"]')
        for img in imgs:
            src = await img.get_attribute('src')
            if src:
                src = re.sub(r'/\d+x\d+\.', '/375x500.', src)
                return src

    except Exception:
        pass

    return None


async def download_image(url: str) -> Optional[bytes]:
    """Download an image and return its bytes."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.fragrantica.com/',
    }

    try:
        if httpx:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.content
        else:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass

    return None


def process_image(image_data: bytes, output_path: Path) -> bool:
    """Resize image and save as WebP."""
    try:
        img = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary (e.g., RGBA or palette mode)
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (10, 10, 10))  # Dark background
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize maintaining aspect ratio
        img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.LANCZOS)

        # Save as WebP
        img.save(str(output_path), 'WEBP', quality=WEBP_QUALITY)
        return True

    except Exception as e:
        print(f"    [!] Image processing error: {e}")
        return False


def load_checkpoint() -> dict:
    """Load progress checkpoint."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"completed": {}, "failed": [], "stats": {"searched": 0, "found": 0, "downloaded": 0}}


def save_checkpoint(checkpoint: dict):
    """Save progress checkpoint."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)


async def run_pipeline(max_items: Optional[int] = None, dry_run: bool = False):
    """Main pipeline: search Fragrantica, download images, update products.json."""

    # Load products
    with open(PRODUCTS_FILE) as f:
        products = json.load(f)

    print(f"Loaded {len(products)} products")

    # Group by fragrance
    groups = group_products(products)
    print(f"Grouped into {len(groups)} unique fragrances (excluding gift sets)")

    # Load checkpoint
    checkpoint = load_checkpoint()
    completed = checkpoint["completed"]  # query -> {image_file, fragrantica_url}
    stats = checkpoint["stats"]

    # Filter to uncompleted
    todo = {q: prods for q, prods in groups.items() if q not in completed and q not in checkpoint.get("failed", [])}
    print(f"Already completed: {len(completed)}")
    print(f"Remaining: {len(todo)}")

    if max_items:
        todo_items = list(todo.items())[:max_items]
    else:
        todo_items = list(todo.items())

    if dry_run:
        print("\n[DRY RUN] Would search for:")
        for q, prods in todo_items[:20]:
            print(f"  \"{q}\" ({len(prods)} products)")
        if len(todo_items) > 20:
            print(f"  ... and {len(todo_items) - 20} more")
        return

    if not todo_items:
        print("Nothing to do! All fragrances have been processed.")
        print("Updating products.json with image paths...")
        update_products_json(products, completed)
        return

    print(f"\nStarting image pipeline for {len(todo_items)} fragrances...")
    print(f"Estimated time: ~{len(todo_items) * 3 / 60:.0f} minutes\n")

    # Ensure images directory exists
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        found_count = 0
        fail_count = 0
        start_time = time.time()

        for i, (query, prods) in enumerate(todo_items):
            elapsed = time.time() - start_time
            rate = (i + 1) / max(elapsed, 1) * 3600
            remaining = (len(todo_items) - i) / max(rate / 3600, 0.001)

            print(f"[{i+1}/{len(todo_items)}] Searching: \"{query}\" ({len(prods)} products) "
                  f"[{found_count} found, {fail_count} missed, ~{remaining:.0f}min left]")

            # Search for the product page
            product_url = await search_fragrantica(page, query)
            stats["searched"] += 1

            if not product_url:
                print(f"    [-] No results found")
                checkpoint.setdefault("failed", []).append(query)
                fail_count += 1
                await asyncio.sleep(DELAY_BETWEEN_SEARCHES)
                continue

            # Get the image URL from the product page
            image_url = await get_product_image_url(page, product_url)
            stats["found"] += 1

            if not image_url:
                print(f"    [-] No image on page: {product_url}")
                checkpoint.setdefault("failed", []).append(query)
                fail_count += 1
                await asyncio.sleep(DELAY_BETWEEN_SEARCHES)
                continue

            # Download the image
            image_data = await download_image(image_url)

            if not image_data:
                print(f"    [-] Download failed: {image_url}")
                checkpoint.setdefault("failed", []).append(query)
                fail_count += 1
                await asyncio.sleep(DELAY_BETWEEN_SEARCHES)
                continue

            # Process and save
            filename = make_image_filename(query)
            output_path = IMAGES_DIR / filename

            if process_image(image_data, output_path):
                file_size = output_path.stat().st_size / 1024
                print(f"    [+] Saved: {filename} ({file_size:.1f} KB)")
                completed[query] = {
                    "image_file": f"/images/products/{filename}",
                    "fragrantica_url": product_url,
                }
                found_count += 1
                stats["downloaded"] += 1
            else:
                checkpoint.setdefault("failed", []).append(query)
                fail_count += 1

            # Save checkpoint every 10 items
            if (i + 1) % 10 == 0:
                save_checkpoint(checkpoint)

            # Rate limit
            await asyncio.sleep(DELAY_BETWEEN_SEARCHES)

        await browser.close()

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Update products.json
    print(f"\n{'='*60}")
    print(f"Pipeline complete!")
    print(f"  Searched: {stats['searched']}")
    print(f"  Found:    {stats['found']}")
    print(f"  Downloaded: {stats['downloaded']}")
    print(f"  Coverage: {stats['downloaded']}/{len(groups)} ({stats['downloaded']/max(len(groups),1)*100:.1f}%)")
    print(f"{'='*60}")

    update_products_json(products, completed)


def update_products_json(products: list, completed: dict):
    """Update products.json with image paths from completed downloads."""
    updated = 0
    for p in products:
        query = clean_search_query(p['raw_name'])
        if query in completed:
            info = completed[query]
            p['image_url'] = info['image_file']
            p['has_image'] = True
            updated += 1

    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f, indent=2)

    total_with_images = sum(1 for p in products if p.get('has_image'))
    print(f"\nUpdated products.json: {total_with_images}/{len(products)} products now have images ({total_with_images/len(products)*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch fragrance images from Fragrantica")
    parser.add_argument("--max", type=int, default=None, help="Max fragrances to process")
    parser.add_argument("--reset", action="store_true", help="Clear checkpoint and start fresh")
    parser.add_argument("--dry-run", action="store_true", help="Show queries without downloading")
    args = parser.parse_args()

    if args.reset and CHECKPOINT_FILE.exists():
        os.remove(CHECKPOINT_FILE)
        print("Checkpoint cleared.")

    asyncio.run(run_pipeline(max_items=args.max, dry_run=args.dry_run))
