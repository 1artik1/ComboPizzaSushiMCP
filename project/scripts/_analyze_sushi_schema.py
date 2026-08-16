# -*- coding: utf-8 -*-
"""sushi_time_schema.py — анализ JSON-LD и весов из HTML sushi_time."""

import re
import json
from collections import Counter

html_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\sushi_time_http.html"

with open(html_path, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

print(f"HTML size: {len(html)}")

# 1. JSON-LD blocks
ld_blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nJSON-LD blocks: {len(ld_blocks)}")

for i, block in enumerate(ld_blocks[:5]):
    print(f"\n--- Block {i} ---")
    try:
        data = json.loads(block)
        print(json.dumps(data, ensure_ascii=False)[:800])
    except Exception as e:
        print(f"  JSON parse error: {e}")
        print(f"  Content: {block[:300]}")

# 2. itemprop="price" spans
price_spans = re.findall(r'<span[^>]*itemprop="price"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\nitemprop=price spans: {len(price_spans)}")
for p in price_spans[:5]:
    clean = re.sub(r'\s+', '', p).strip()
    print(f"  price: '{clean}'")

# 3. vess_preview spans
weight_spans = re.findall(r'<span[^>]*id="vess_preview_(\d+)"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\nvess_preview spans (id, text): {len(weight_spans)}")
for wid, wt in weight_spans[:5]:
    clean = re.sub(r'\s+', '', wt).strip()
    print(f"  id={wid} weight: '{clean}'")

# 4. data-title and data-id on cards
# Find all product cards with data-id
cards = re.findall(r'data-id="(\d+)"[^>]*data-title="([^"]*)"[^>]*data-category-name="([^"]*)"', html, re.DOTALL)
print(f"\nCards with (id, title, cat): {len(cards)}")
cat_counts = Counter()
for cid, title, cat in cards[:10]:
    cat_counts[cat] += 1
    print(f"  id={cid} title='{title}' cat='{cat}'")
print(f"Categories: {cat_counts.most_common(10)}")

# 5. Also check for separate data-title (not necessarily on same element)
all_titles = re.findall(r'data-title="([^"]*)"', html)
print(f"\nAll data-title: {len(all_titles)}")
unique_titles = set(all_titles)
print(f"Unique titles: {len(unique_titles)}")

# 6. Check if price is in JSON-LD as number or string
print("\n--- Analyzing JSON-LD price format ---")
for i, block in enumerate(ld_blocks):
    try:
        data = json.loads(block)
        # Check if it's a product
        if isinstance(data, dict) and data.get("@type") == "Product":
            print(f"\nBlock {i} is Product")
            print(f"  name: {data.get('name', '')}")
            print(f"  offers: {json.dumps(data.get('offers', {}), ensure_ascii=False)}")
            print(f"  category: {data.get('category', '')}")
        elif isinstance(data, dict) and data.get("@type") == "WebPage":
            print(f"\nBlock {i} is WebPage")
        elif isinstance(data, list):
            for j, item in enumerate(data[:2]):
                print(f"\nBlock {i}[{j}] type={item.get('@type', '')}")
                if item.get("@type") == "Product":
                    print(f"  name: {item.get('name', '')}")
                    print(f"  offers: {json.dumps(item.get('offers', {}), ensure_ascii=False)}")
    except Exception:
        pass
