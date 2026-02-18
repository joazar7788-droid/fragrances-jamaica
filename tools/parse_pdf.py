#!/usr/bin/env python3
"""
Fragrances Jamaica — PDF to JSON Data Pipeline

Parses the "Fragrance Price List.pdf" into structured product data.
Handles PDF quirks: ligature corruption, multi-line entries, column overlap.

Usage:
    python tools/parse_pdf.py

Output:
    data/products.json  — Full product array
    data/brands.json    — Unique brands with counts
    data/stats.json     — Category statistics
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import pdfplumber

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
PDF_PATH = PROJECT_DIR.parent / "Fragrance Price List.pdf"
DATA_DIR = PROJECT_DIR / "data"

# ─── Brand Dictionary ────────────────────────────────────────────────────────
# Sorted longest-first so "Dolce & Gabbana" matches before "Dolce"
KNOWN_BRANDS = sorted([
    # === Product lines used as brands in the PDF ===
    "1 Million", "1 And Only", "1 New Give",
    "212 VIP", "212 Heroes", "212 Sexy", "212",
    "360 Collection", "360",

    # === Multi-word fragrance house brands ===
    "Dolce & Gabbana", "Tom Ford", "Carolina Herrera", "Ralph Lauren",
    "Clive Christian", "Bond No.9", "Bond No. 9",
    "Maison Francis Kurkdjian", "Maison Martin Margiela", "Maison Margiela",
    "Acqua di Parma", "Acqua Di Parma", "Acqua Di Gio", "Acqua di Gio",
    "Al Haramain", "Narciso Rodriguez", "Vince Camuto",
    "Perry Ellis", "Mont Blanc", "Montblanc", "Hugo Boss",
    "Calvin Klein", "Issey Miyake", "Jean Paul Gaultier",
    "Paco Rabanne", "Yves Saint Laurent", "Giorgio Armani",
    "Abercrombie and Fitch", "Abercrombie & Fitch",
    "Antonio Banderas", "Paris Hilton", "Nicki Minaj",
    "Britney Spears", "Sarah Jessica Parker", "Jessica Simpson",
    "Elizabeth Arden", "Elizabeth Taylor", "Estee Lauder",
    "Van Cleef", "Van Cleef & Arpels",
    "Oscar de la Renta", "Juicy Couture", "Marc Jacobs",
    "Michael Kors", "Roberto Cavalli", "Salvatore Ferragamo",
    "Cristiano Ronaldo", "David Beckham", "Sean John",
    "Ed Hardy", "English Laundry", "French Connection",
    "Geoffrey Beene", "Halle Berry",
    "Jennifer Lopez", "Jennifer Aniston", "John Varvatos",
    "Jordi Fernandez", "Kenneth Cole", "Liz Claiborne",
    "Nanette Lepore", "Nicole Miller", "Nine West", "Paris Bleu",
    "Robert Graham", "Rochas",
    "Swiss Army", "Swiss Arabian", "Tommy Bahama",
    "Tommy Hilfiger", "Vera Wang",
    "Club de Nuit", "Armaf Club",
    "Viktor & Rolf", "Viktor and Rolf",
    "Mercedes Benz", "Mercedes-Benz",
    "Alfred Sung", "Anna Sui", "Banana Republic",
    "Bill Blass", "Bob Mackie", "Bottega Veneta",
    "Burberry Brit", "Celine Dion", "Christian Audigier",
    "Coach New York", "Donna Karan", "Elie Saab",
    "Ermenegildo Zegna", "Giorgio Beverly Hills",
    "Miu Miu", "Nina Ricci",
    "Pierre Cardin", "Stella McCartney",
    "Tiffany & Co", "Tory Burch",
    "Clean Reserve", "Costume National",
    "Ariana Grande", "Agent Provocateur",

    # === Product-line brands found in PDF data ===
    "Daniel Josier", "Daniel Hechter",
    "The Lion's Club", "The Dreamer", "The Golden Secret",
    "The Icon", "The Key", "The Bewitching",
    "Black Seduction", "Black Bold", "Black Point",
    "Black Is Black", "Black One", "Black Opium",
    "Blue Seduction", "Blue De Chanel",
    "Light Blue", "Cool Water",
    "Good Girl", "Bad Boy", "Bad Girl",
    "Love Dont Be Shy",
    "CH Beasts", "CH Kings", "CH Men", "CH Passion", "CH",
    "Iron Man", "Bright Crystal",
    "Ilmin Il", "Ilmin",
    "Ainash", "AHLI", "Bharara", "Odyssey", "Kilian", "Bebe",
    "Arabia", "Scandal",

    # Product lines commonly used as brand names in the PDF
    "La Vie Est Belle", "La Nuit", "La Rive",
    "Le Male", "Le Beau",
    "Pure Instinct", "Pure Poison", "Pure XS",
    "Eternity", "Invictus", "Curve", "Daisy", "Angel",
    "Territoire", "Insurrection", "Viva La Juicy", "Viva",
    "Rose Seduction", "Rose",
    "Night Life", "Night",
    "Miss Dior", "Miss",
    "Eau Sauvage",
    "Be Delicious",

    # === Single-word fragrance house brands ===
    "Acqua", "Afnan", "Aigner", "Ajmal", "Amouage", "Animale",
    "Armaf", "Armani", "Aramis", "Atelier", "Atkinsons", "Azzaro",
    "Baldessarini", "Bentley", "Beyonce", "Boucheron", "Brioni",
    "Burberry", "Bvlgari", "Bulgari",
    "Cabotine", "Cacharel", "Cartier", "Carven", "Celine", "Cerruti",
    "Chanel", "Chloe", "Chopard", "Clinique", "Coach", "Creed", "Cuba",
    "Davidoff", "Demeter", "Diesel", "Dior", "DKNY", "Dkny", "Dunhill",
    "Escada", "Fendi", "Ferragamo",
    "Givenchy", "Gritti", "Gucci", "Guess", "Guerlain",
    "Halston", "Halloween", "Hermes", "Hugo",
    "Iceberg", "Initio", "Issey",
    "Jaguar", "Jean", "Jivago", "Joop", "Jovan",
    "Kenzo", "Korloff",
    "Lacoste", "Lagerfeld", "Lalique", "Lancaster", "Lancome", "Lanvin",
    "Lattafa", "Loewe", "Lomani",
    "Mancera", "Marchesa", "MCM", "Memo", "Missoni", "Molinard",
    "Montale", "Moschino", "Mugler",
    "Narciso", "Nautica", "Nishane",
    "Orientica",
    "Paco", "Paloma", "Penhaligons", "Penhaligon's", "Philosophy",
    "Police", "Polo", "Porsche", "Prada", "Puma",
    "Ralph", "Rasasi", "Replay", "Revlon", "Rihanna", "Roberto",
    "Roccobarocco", "Roja", "Romea",
    "Salvatore", "Sergio", "Shakira", "Stetson", "Swarovski",
    "Tabac", "Thierry", "Tiffany", "Tous", "Trussardi",
    "Ungaro", "Usher",
    "Valentino", "Versace", "Vince",
    "Xerjoff", "XERJOFF", "XOXO",
    "YSL", "Yardley",
    "Zadig", "Zakat",

    # === Additional single-word brands from data ===
    "AB Spirit", "Above The Law", "Abstracto",
    "Adidas", "Alaia", "Alexandre",
    "Annick", "Aquolina", "Azzedine",
    "Baby Phat", "Benetton", "Bogart", "Boss", "Brut",
    "Calvin", "CK",
    "Franck", "Gianfranco",
    "Hanae", "Jacques", "Jeanne", "Jimmy", "Juliette",
    "Karl", "Kate", "Kim",
    "Laura", "Lolita", "Luciano",
    "Mandarina", "Masaki", "Max", "Mexx", "Michael", "Molton",
    "Nikos",
    "Pacifica", "Puma",
    "Rag",
    "Sean", "Sofia", "Stella",
    "Ted",
    "Van",

    "Stallion", "Sung",
    "4711", "786", "9 AM", "9 PM",
    "AB Spirit Millionaire",
], key=len, reverse=True)


# ─── Ligature Fixes ──────────────────────────────────────────────────────────
LIGATURE_FIXES = {
    "Re llable": "Refillable",
    "Re ll ": "Refill ",
    "con dential": "confidential",
    "Of cial": "Official",
    "of cial": "official",
    "Magni cent": "Magnificent",
    "Beauti ful": "Beautiful",
    "Signi cant": "Significant",
}


def fix_ligatures(text: str) -> str:
    """Fix common ligature corruption from PDF extraction."""
    for broken, fixed in LIGATURE_FIXES.items():
        text = text.replace(broken, fixed)
    # Fix standalone fi/fl/ff ligature artifacts
    text = re.sub(r'\bfi\b(?!\w)', '', text)  # Remove isolated 'fi'
    text = re.sub(r'\bfl\b(?!\w)', '', text)
    text = re.sub(r'\bff\b(?!\w)', '', text)
    return text.strip()


# ─── Fragrance Type Normalization ─────────────────────────────────────────────
TYPE_MAP = {
    "edp": "EDP",
    "edt": "EDT",
    "edc": "EDC",
    "parfum": "Parfum",
    "parfum intense": "Parfum Intense",
    "cologne": "Cologne",
    "body mist": "Body Mist",
    "body spray": "Body Spray",
    "eau de parfum": "EDP",
    "eau de toilette": "EDT",
    "eau de cologne": "EDC",
    "le parfum": "Le Parfum",
}


def normalize_type(raw_type: str) -> str:
    """Normalize fragrance type to standard abbreviation."""
    return TYPE_MAP.get(raw_type.lower().strip(), raw_type.strip())


# ─── Line Parser ──────────────────────────────────────────────────────────────
# Pattern: item_name  UPC_number  price
# The UPC is a long digit string (8-16 digits), price is a float
LINE_PATTERN = re.compile(
    r'^(.*?)\s+(\d{5,20})\s+(\d+\.?\d*)\s*$'
)

# Some lines only have item_name and price (no UPC)
LINE_NO_UPC = re.compile(
    r'^(.*?)\s{2,}(\d+\.?\d*)\s*$'
)

# Header pattern to skip
HEADER_PATTERN = re.compile(r'^\s*Item\s+UPC\s+Retail', re.IGNORECASE)


def parse_line(line: str) -> Optional[dict]:
    """Parse a single line from the PDF into a product dict."""
    line = line.strip()
    if not line or HEADER_PATTERN.match(line):
        return None

    # Skip page numbers (standalone numbers)
    if re.match(r'^\d{1,3}$', line):
        return None

    # Skip the unicode replacement character lines
    if line.strip() in ('', '\ufffd'):
        return None

    # Try full pattern: item UPC price
    match = LINE_PATTERN.match(line)
    if match:
        item_name = match.group(1).strip()
        upc = match.group(2).strip()
        price_str = match.group(3).strip()
        if item_name and len(item_name) > 3:
            return {
                "raw_name": item_name,
                "upc": upc,
                "raw_price": price_str,
            }

    # Try pattern without UPC: item price
    match2 = LINE_NO_UPC.match(line)
    if match2:
        item_name = match2.group(1).strip()
        price_str = match2.group(2).strip()
        if item_name and len(item_name) > 3:
            return {
                "raw_name": item_name,
                "upc": "",
                "raw_price": price_str,
            }

    # Item name only (no UPC, no price)
    if re.search(r'(for men|for women|for woman|unisex|gift set)', line, re.IGNORECASE):
        return {
            "raw_name": line,
            "upc": "",
            "raw_price": None,
        }

    return None


# ─── Field Extraction ─────────────────────────────────────────────────────────
def extract_gender(name: str) -> str:
    """Extract gender from product name."""
    lower = name.lower()
    if re.search(r'\bfor\s+men\b', lower):
        return "men"
    elif re.search(r'\bfor\s+wom[ae]n\b', lower):
        return "women"
    elif re.search(r'\bunisex\b', lower):
        return "unisex"
    # Default based on section context would be ideal but we'll use unisex
    return "unisex"


def extract_size(name: str) -> Optional[str]:
    """Extract size (e.g., '3.4 oz') from product name."""
    match = re.search(r'(\d+\.?\d*)\s*oz', name, re.IGNORECASE)
    if match:
        size_val = match.group(1)
        # Normalize: remove trailing zeros but keep one decimal
        try:
            num = float(size_val)
            if num == int(num):
                return f"{int(num)} oz"
            return f"{num} oz"
        except ValueError:
            return f"{size_val} oz"
    return None


def extract_type(name: str) -> Optional[str]:
    """Extract fragrance type from product name."""
    # Order matters: check longer types first
    type_patterns = [
        r'\bParfum\s+Intense\b',
        r'\bLe\s+Parfum\b',
        r'\bEau\s+de\s+Parfum\b',
        r'\bEau\s+de\s+Toilette\b',
        r'\bEau\s+de\s+Cologne\b',
        r'\bBody\s+Mist\b',
        r'\bBody\s+Spray\b',
        r'\bEDP\b',
        r'\bEDT\b',
        r'\bEDC\b',
        r'\bParfum\b',
        r'\bCologne\b',
    ]
    for pattern in type_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            return normalize_type(match.group(0))
    return None


def extract_brand(name: str) -> str:
    """Extract brand from product name using longest-match-first dictionary."""
    name_lower = name.lower()
    for brand in KNOWN_BRANDS:
        brand_lower = brand.lower()
        if name_lower.startswith(brand_lower):
            # Make sure we're matching at a word boundary
            next_char_idx = len(brand)
            if next_char_idx >= len(name) or not name[next_char_idx].isalpha():
                return brand
        # Also check with "by" pattern: "Product by Brand"
    # Check "by Brand" pattern
    by_match = re.search(r'\bby\s+(.+?)(?:\s+\d|\s+for\b)', name, re.IGNORECASE)
    if by_match:
        potential_brand = by_match.group(1).strip()
        for brand in KNOWN_BRANDS:
            if potential_brand.lower().startswith(brand.lower()):
                return brand

    # Fallback: first word(s) as brand
    words = name.split()
    if words:
        return words[0]
    return "Unknown"


def extract_display_name(raw_name: str, brand: str) -> str:
    """Extract the display name (product name without brand, size, type, gender)."""
    name = raw_name

    # Remove brand prefix
    if name.lower().startswith(brand.lower()):
        name = name[len(brand):].strip()

    # Remove size
    name = re.sub(r'\d+\.?\d*\s*oz', '', name, flags=re.IGNORECASE)

    # Remove type
    for pattern in [
        r'\bParfum\s+Intense\b', r'\bLe\s+Parfum\b',
        r'\bEau\s+de\s+Parfum\b', r'\bEau\s+de\s+Toilette\b',
        r'\bEau\s+de\s+Cologne\b', r'\bBody\s+Mist\b',
        r'\bBody\s+Spray\b', r'\bEDP\b', r'\bEDT\b', r'\bEDC\b',
        r'\bParfum\b', r'\bCologne\b',
    ]:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Remove gender
    name = re.sub(r'\bfor\s+(men|women|woman|unisex)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bUnisex\b', '', name, flags=re.IGNORECASE)

    # Remove "Piece Gift Set" and similar
    name = re.sub(r'\d+\s*Piece\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bGift\s+Set\b', 'Gift Set', name, flags=re.IGNORECASE)

    # Remove "by Brand" suffix
    name = re.sub(r'\bby\s+\w+.*$', '', name, flags=re.IGNORECASE)

    # Clean up extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    # If nothing left, use the raw name portion
    if not name or len(name) < 2:
        # Use raw_name minus brand
        name = raw_name
        if name.lower().startswith(brand.lower()):
            name = name[len(brand):].strip()
        if not name:
            name = raw_name

    return name


def make_id(raw_name: str) -> str:
    """Generate a URL-friendly ID from the product name."""
    slug = raw_name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug[:80]  # Max 80 chars


def normalize_price(raw_price: Optional[str]) -> Optional[float]:
    """Normalize price to a float, or None if missing/zero."""
    if not raw_price:
        return None
    try:
        price = float(raw_price)
        if price <= 0:
            return None
        return round(price, 2)
    except ValueError:
        return None


# ─── Main Pipeline ────────────────────────────────────────────────────────────
def extract_products_from_pdf(pdf_path: str) -> List[dict]:
    """Extract all products from the PDF."""
    raw_products = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text(layout=True)
            if not text:
                continue

            lines = text.split('\n')
            for line in lines:
                line = fix_ligatures(line)
                product = parse_line(line)
                if product:
                    raw_products.append(product)

    return raw_products


def process_products(raw_products):
    """Process raw products into structured data."""
    products = []
    seen_ids = set()
    unrecognized_brands = Counter()
    parse_failures = []

    for raw in raw_products:
        raw_name = raw["raw_name"]
        upc = raw.get("upc", "")
        price = normalize_price(raw.get("raw_price"))

        # Extract fields
        gender = extract_gender(raw_name)
        size = extract_size(raw_name)
        frag_type = extract_type(raw_name)
        is_gift_set = bool(re.search(r'gift\s*set', raw_name, re.IGNORECASE))
        is_tester = bool(re.search(r'\bTESTER\b', raw_name, re.IGNORECASE))
        brand = extract_brand(raw_name)
        display_name = extract_display_name(raw_name, brand)

        # Generate unique ID
        base_id = make_id(raw_name)
        product_id = base_id
        counter = 1
        while product_id in seen_ids:
            product_id = f"{base_id}-{counter}"
            counter += 1
        seen_ids.add(product_id)

        # Track unrecognized brands (single-word fallbacks)
        if brand == raw_name.split()[0] if raw_name.split() else "Unknown":
            brand_lower = brand.lower()
            if brand_lower not in {b.lower() for b in KNOWN_BRANDS}:
                unrecognized_brands[brand] += 1

        products.append({
            "id": product_id,
            "raw_name": raw_name,
            "brand": brand,
            "name": display_name,
            "size": size,
            "type": frag_type,
            "gender": gender,
            "price": price,
            "upc": upc,
            "is_gift_set": is_gift_set,
            "is_tester": is_tester,
            "image_url": None,
            "has_image": False,
        })

    return products, unrecognized_brands


def generate_brands(products) -> List[dict]:
    """Generate brand list with product counts."""
    brand_counts = Counter(p["brand"] for p in products)
    brands = [
        {"name": brand, "count": count}
        for brand, count in sorted(brand_counts.items(), key=lambda x: x[0].lower())
    ]
    return brands


def generate_stats(products) -> dict:
    """Generate statistics for the catalog."""
    gender_counts = Counter(p["gender"] for p in products)
    type_counts = Counter(p["type"] for p in products if p["type"])
    size_counts = Counter(p["size"] for p in products if p["size"])
    prices = [p["price"] for p in products if p["price"] is not None]

    return {
        "total_products": len(products),
        "by_gender": dict(gender_counts),
        "by_type": dict(type_counts.most_common(20)),
        "by_size": dict(size_counts.most_common(20)),
        "price_range": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "avg": round(sum(prices) / len(prices), 2) if prices else 0,
        },
        "missing_prices": sum(1 for p in products if p["price"] is None),
        "gift_sets": sum(1 for p in products if p["is_gift_set"]),
        "testers": sum(1 for p in products if p["is_tester"]),
        "with_images": sum(1 for p in products if p["has_image"]),
    }


def main():
    print("=" * 60)
    print("Fragrances Jamaica — PDF Data Pipeline")
    print("=" * 60)

    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        sys.exit(1)

    # Step 1: Extract raw products
    print(f"\n[1/4] Extracting products from PDF...")
    raw_products = extract_products_from_pdf(str(PDF_PATH))
    print(f"  Raw products extracted: {len(raw_products)}")

    # Step 2: Process into structured data
    print(f"\n[2/4] Processing product data...")
    result = process_products(raw_products)
    products = result[0]
    unrecognized_brands = result[1]
    print(f"  Processed products: {len(products)}")

    # Step 3: Generate supporting data
    print(f"\n[3/4] Generating brands and stats...")
    brands = generate_brands(products)
    stats = generate_stats(products)

    # Step 4: Write output files
    print(f"\n[4/4] Writing output files...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(DATA_DIR / "products.json", "w") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"  Written: data/products.json ({len(products)} products)")

    with open(DATA_DIR / "brands.json", "w") as f:
        json.dump(brands, f, indent=2, ensure_ascii=False)
    print(f"  Written: data/brands.json ({len(brands)} brands)")

    with open(DATA_DIR / "stats.json", "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"  Written: data/stats.json")

    # Validation Report
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    print(f"\nTotal products: {stats['total_products']}")
    print(f"\nBy gender:")
    for gender, count in sorted(stats['by_gender'].items()):
        print(f"  {gender}: {count}")
    print(f"\nBy type (top 10):")
    for type_name, count in list(stats['by_type'].items())[:10]:
        print(f"  {type_name}: {count}")
    print(f"\nPrice range: ${stats['price_range']['min']:.2f} - ${stats['price_range']['max']:.2f}")
    print(f"Average price: ${stats['price_range']['avg']:.2f}")
    print(f"Missing prices: {stats['missing_prices']}")
    print(f"Gift sets: {stats['gift_sets']}")
    print(f"Testers: {stats['testers']}")
    print(f"Unique brands: {len(brands)}")

    if unrecognized_brands:
        print(f"\nUnrecognized brands (top 20 — may need adding to dictionary):")
        for brand, count in unrecognized_brands.most_common(20):
            print(f"  {brand}: {count}")

    # Show some sample products for verification
    print(f"\nSample products (first 5):")
    for p in products[:5]:
        print(f"  [{p['brand']}] {p['name']} | {p['size']} | {p['type']} | {p['gender']} | ${p['price']}")

    print(f"\nSample products (random from middle):")
    mid = len(products) // 2
    for p in products[mid:mid+5]:
        print(f"  [{p['brand']}] {p['name']} | {p['size']} | {p['type']} | {p['gender']} | ${p['price']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
