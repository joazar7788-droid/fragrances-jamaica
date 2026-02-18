#!/usr/bin/env python3
"""
Fragrantica Image Pipeline
==========================
Searches Fragrantica for product images using Playwright (headless browser),
downloads bottle images, converts to WebP, and updates products.json.

Features:
- Resumable: saves progress to a checkpoint file
- Rate-limit aware: detects 429 pages, pauses, and retries with backoff
- Groups products by fragrance to minimize searches
- Skips gift sets (no standard product images)

Usage:
    python3 tools/fetch_images.py [--max N] [--reset] [--reset-failed] [--dry-run]
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
from typing import Optional, Dict, List
from collections import defaultdict

try:
    from playwright.async_api import async_playwright, Page
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
BASE_DELAY = 5.0          # seconds between requests
JITTER = 2.0              # random jitter added to delay
RATE_LIMIT_PAUSE = 300.0  # 5 minutes pause on rate limit
SEARCH_TIMEOUT = 15000    # ms


def clean_search_query(raw_name: str) -> str:
    """Extract a clean fragrance name for searching Fragrantica."""
    q = raw_name
    q = re.sub(r'\d+\.?\d*\s*oz\.?', '', q)
    for t in ['EDP', 'EDT', 'EDC', 'Parfum', 'Cologne', 'Body Mist', 'Body Spray',
              'Eau De Parfum', 'Eau De Toilette']:
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


def group_products(products: List[dict]) -> Dict[str, List[dict]]:
    """Group products by clean fragrance name for shared image lookup."""
    groups = defaultdict(list)
    for p in products:
        if p.get('is_gift_set'):
            continue
        query = clean_search_query(p['raw_name'])
        if len(query) < 3:
            continue
        groups[query].append(p)
    return dict(groups)


def make_image_filename(query: str) -> str:
    """Generate a stable filename from search query."""
    slug = re.sub(r'[^a-z0-9]+', '-', query.lower()).strip('-')
    h = hashlib.md5(query.encode()).hexdigest()[:6]
    return f"{slug[:80]}-{h}.webp"


async def is_rate_limited(page: Page) -> bool:
    """Check if current page shows a rate limit / anti-bot response."""
    try:
        content = await page.content()
        lower = content.lower()
        return any(s in lower for s in ['too many requests', 'giphy.com', 'access denied',
                                         'captcha', 'rate limit'])
    except Exception:
        return False


async def wait_for_rate_limit_clear(page: Page, context_factory):
    """Wait until Fragrantica is accessible again, checking every 5 minutes."""
    print("\n>>> Rate limited. Waiting for it to clear (checking every 5 min)...")
    attempt = 0
    while True:
        attempt += 1
        await asyncio.sleep(RATE_LIMIT_PAUSE)
        print(f"    Checking if rate limit cleared (attempt {attempt})...")
        try:
            # Test with a simple search
            await page.goto('https://www.fragrantica.com/search/?query=chanel',
                          wait_until='domcontentloaded', timeout=SEARCH_TIMEOUT)
            await page.wait_for_timeout(2000)
            if not await is_rate_limited(page):
                print("    >>> Rate limit cleared! Resuming...\n")
                return
            else:
                print(f"    Still rate limited. Waiting another 5 min...")
        except Exception:
            print(f"    Connection error. Waiting another 5 min...")


async def search_and_get_image(page: Page, query: str) -> Optional[dict]:
    """
    Search Fragrantica and extract the product page URL and image.
    Returns dict with 'image_url' and 'fragrantica_url', or None, or "RATE_LIMITED".
    """
    encoded = query.replace(' ', '+')
    search_url = f"https://www.fragrantica.com/search/?query={encoded}"

    try:
        await page.goto(search_url, wait_until='domcontentloaded', timeout=SEARCH_TIMEOUT)
        await page.wait_for_timeout(2000)

        if await is_rate_limited(page):
            return "RATE_LIMITED"

        # Find product links
        results = await page.query_selector_all('a[href*="/perfume/"]')

        best_url = None
        for result in results[:5]:
            href = await result.get_attribute('href')
            if href and '/perfume/' in href and href.endswith('.html'):
                if href.startswith('/'):
                    href = 'https://www.fragrantica.com' + href
                best_url = href
                break

        if not best_url:
            return None

        # Extract Fragrantica product ID from URL to construct image URL directly
        # URL format: /perfume/Brand/Product-Name-12345.html → ID is 12345
        id_match = re.search(r'-(\d+)\.html$', best_url)
        if id_match:
            frag_id = id_match.group(1)
            image_url = f"https://fimgs.net/mdimg/perfume-thumbs/375x500.{frag_id}.jpg"
            return {"image_url": image_url, "fragrantica_url": best_url}

        # Fallback: visit the product page to get the image
        await asyncio.sleep(1.5)
        try:
            await page.goto(best_url, wait_until='domcontentloaded', timeout=SEARCH_TIMEOUT)
            await page.wait_for_timeout(1500)

            if await is_rate_limited(page):
                return "RATE_LIMITED"

            img = await page.query_selector('img[itemprop="image"]')
            if img:
                src = await img.get_attribute('src')
                if src and 'perfume-thumbs' in src:
                    src = re.sub(r'/\d+x\d+\.', '/375x500.', src)
                    return {"image_url": src, "fragrantica_url": best_url}

            imgs = await page.query_selector_all('img[src*="perfume-thumbs"]')
            for img in imgs:
                src = await img.get_attribute('src')
                if src:
                    src = re.sub(r'/\d+x\d+\.', '/375x500.', src)
                    return {"image_url": src, "fragrantica_url": best_url}
        except Exception:
            pass

    except Exception:
        pass

    return None


async def download_image(url: str) -> Optional[bytes]:
    """Download an image from the CDN."""
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


def update_products_json(products: list, completed: dict):
    """Update products.json with image paths from completed downloads."""
    for p in products:
        query = clean_search_query(p['raw_name'])
        if query in completed:
            p['image_url'] = completed[query]['image_file']
            p['has_image'] = True

    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f, indent=2)

    total = sum(1 for p in products if p.get('has_image'))
    print(f"    products.json updated: {total}/{len(products)} have images ({total/len(products)*100:.1f}%)")


async def run_pipeline(max_items: Optional[int] = None, dry_run: bool = False):
    with open(PRODUCTS_FILE) as f:
        products = json.load(f)

    print(f"Loaded {len(products)} products")

    groups = group_products(products)
    print(f"{len(groups)} unique fragrances (excluding gift sets)")

    checkpoint = load_checkpoint()
    completed = checkpoint["completed"]
    stats = checkpoint["stats"]
    failed_set = set(checkpoint.get("failed", []))

    todo = {q: prods for q, prods in groups.items()
            if q not in completed and q not in failed_set}

    print(f"Completed: {len(completed)} | Failed: {len(failed_set)} | Remaining: {len(todo)}")

    todo_items = list(todo.items())
    if max_items:
        todo_items = todo_items[:max_items]

    if dry_run:
        print(f"\n[DRY RUN] Would search for {len(todo_items)} fragrances")
        for q, prods in todo_items[:20]:
            print(f"  \"{q}\" ({len(prods)} products)")
        return

    if not todo_items:
        print("Nothing new to process.")
        update_products_json(products, completed)
        return

    est_hours = len(todo_items) * (BASE_DELAY + JITTER/2) / 3600
    print(f"\nProcessing {len(todo_items)} fragrances (~{est_hours:.1f} hours at {BASE_DELAY}s delay)")
    print(f"Start time: {time.strftime('%H:%M:%S')}\n")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        # First: wait until rate limit clears
        print("Checking if Fragrantica is accessible...")
        await page.goto('https://www.fragrantica.com/search/?query=chanel',
                       wait_until='domcontentloaded', timeout=SEARCH_TIMEOUT)
        await page.wait_for_timeout(2000)
        if await is_rate_limited(page):
            await wait_for_rate_limit_clear(page, None)

        found = 0
        missed = 0
        start_time = time.time()

        for i, (query, prods) in enumerate(todo_items):
            elapsed = time.time() - start_time
            rate_per_sec = max((i + 1) / max(elapsed, 1), 0.001)
            remaining_min = (len(todo_items) - i) / rate_per_sec / 60

            print(f"[{i+1}/{len(todo_items)}] \"{query}\" ({len(prods)} prods) "
                  f"[{found} ok, {missed} miss, ~{remaining_min:.0f}m]")

            result = await search_and_get_image(page, query)

            # Handle rate limiting with wait-and-retry
            if result == "RATE_LIMITED":
                await wait_for_rate_limit_clear(page, None)
                # Retry this query
                result = await search_and_get_image(page, query)
                if result == "RATE_LIMITED":
                    print("    Still limited after wait. Skipping for now.")
                    await asyncio.sleep(BASE_DELAY)
                    continue

            stats["searched"] = stats.get("searched", 0) + 1

            if result is None:
                missed += 1
                checkpoint.setdefault("failed", []).append(query)
                await asyncio.sleep(BASE_DELAY + random.uniform(0, JITTER))
                continue

            # Download image from CDN (not rate-limited)
            image_data = await download_image(result["image_url"])

            if not image_data:
                missed += 1
                checkpoint.setdefault("failed", []).append(query)
                await asyncio.sleep(BASE_DELAY + random.uniform(0, JITTER))
                continue

            filename = make_image_filename(query)
            output_path = IMAGES_DIR / filename

            if process_image(image_data, output_path):
                kb = output_path.stat().st_size / 1024
                print(f"    [+] {filename} ({kb:.1f}KB)")
                completed[query] = {
                    "image_file": f"/images/products/{filename}",
                    "fragrantica_url": result["fragrantica_url"],
                }
                found += 1
                stats["downloaded"] = stats.get("downloaded", 0) + 1
            else:
                missed += 1
                checkpoint.setdefault("failed", []).append(query)

            # Save checkpoint every 10, update products.json every 100
            if (i + 1) % 10 == 0:
                save_checkpoint(checkpoint)
            if (i + 1) % 100 == 0:
                update_products_json(products, completed)

            await asyncio.sleep(BASE_DELAY + random.uniform(0, JITTER))

        await browser.close()

    save_checkpoint(checkpoint)

    total_elapsed = (time.time() - start_time) / 60
    print(f"\n{'='*60}")
    print(f"Pipeline complete! ({total_elapsed:.0f} minutes)")
    print(f"  Downloaded: {found}")
    print(f"  Missed: {missed}")
    print(f"  Total coverage: {len(completed)}/{len(groups)} ({len(completed)/max(len(groups),1)*100:.1f}%)")
    print(f"{'='*60}")

    update_products_json(products, completed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch fragrance images from Fragrantica")
    parser.add_argument("--max", type=int, default=None, help="Max fragrances to process")
    parser.add_argument("--reset", action="store_true", help="Clear checkpoint and start fresh")
    parser.add_argument("--reset-failed", action="store_true", help="Clear failed list only (retry)")
    parser.add_argument("--dry-run", action="store_true", help="Show queries without downloading")
    args = parser.parse_args()

    if args.reset and CHECKPOINT_FILE.exists():
        os.remove(CHECKPOINT_FILE)
        print("Checkpoint cleared.")
    elif args.reset_failed and CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            cp = json.load(f)
        cp["failed"] = []
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(cp, f, indent=2)
        print("Failed list cleared.")

    asyncio.run(run_pipeline(max_items=args.max, dry_run=args.dry_run))
