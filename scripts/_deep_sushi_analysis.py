# -*- coding: utf-8 -*-
"""deep_sushi_analysis.py — ищем цены в sushi_time HTML."""

import re
import json
from collections import Counter

html_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\sushi_time_http.html"
with open(html_path, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

# 1. Look for price patterns in the HTML
# Check for data-price attributes
data_prices = re.findall(r'data-price="([^"]+)"', html)
print(f"data-price attributes: {len(data_prices)}")
for dp in data_prices[:5]:
    print(f"  data-price: '{dp}'")

# 2. Check for script blocks with product data
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nScript blocks: {len(scripts)}")

# Look for JSON-like product data in scripts
for i, script in enumerate(scripts):
    # Check if it contains product data
    if '"name"' in script and ('"price"' in script or '"offers"' in script):
        print(f"\nScript {i} has product data (first 500 chars):")
        print(script[:500])
        break

# 3. Look for meta tags with prices
meta_prices = re.findall(r'<meta[^>]*content="([^"]*[\d]\s*\d+[\s]*[\u041f\u20bd\u00a0\u0440\u0443\u043b][^"]*)"[^>]*itemprop="price"', html)
print(f"\nMeta price tags: {len(meta_prices)}")

# 4. Check for structured data in <div> with itemtype
itemtype_divs = re.findall(r'<div[^>]*itemtype="http://schema.org/Product"[^>]*>(.*?)</div>', html, re.DOTALL)
print(f"Schema.org Product divs: {len(itemtype_divs)}")

# 5. Check for JSON in script type=json-ld
json_ld = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nJSON-LD script blocks: {len(json_ld)}")
for i, block in enumerate(json_ld):
    print(f"Block {i}: {block[:200]}")

# 6. Look for any price-like patterns
# Find all numbers followed by currency symbols
price_pattern = re.findall(r'\b(\d+)\s*[₽\u041f\u00a0\u0440\u0443\u043b]|(\d+)\s*руб', html)
print(f"\nPrice patterns (number, symbol): {len(price_pattern)}")
for p in price_pattern[:10]:
    print(f"  {p}")

# 7. Check for class names that might contain price info
class_pattern = re.findall(r'(\w*price\w*)', html, re.IGNORECASE)
print(f"\nClasses with 'price': {Counter(class_pattern).most_common(10)}")

# 8. Look for the specific structure around data-id
# Find all divs with data-id and examine their content
all_data_ids = re.findall(r'data-id="(\d+)"', html)
print(f"\nTotal data-id occurrences: {len(all_data_ids)}")
unique_ids = set(all_data_ids)
print(f"Unique data-id values: {len(unique_ids)}")

# 9. Check for JSON embedded in JS variables
js_vars = re.findall(r'var\s+(\w+)\s*=\s*(\{.*?\});', html, re.DOTALL)
print(f"\nJS variables with object: {len(js_vars)}")
for var_name, var_val in js_vars[:5]:
    print(f"  {var_name}: {var_val[:200]}")

# 10. Look for window.__INITIAL_STATE__ or similar
init_state = re.findall(r'window\.__INITIAL_STATE__\s*=\s*(.*?);', html, re.DOTALL)
print(f"\nwindow.__INITIAL_STATE__: {len(init_state)}")
for s in init_state[:2]:
    print(f"  {s[:300]}")

# 11. Check for data attributes on product cards
# Find all elements with data- attributes near data-id
card_pattern = re.findall(r'data-id="(\d+)"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
print(f"\nCards with data-id (first 2): {len(card_pattern)}")
for cid, content in card_pattern[:2]:
    print(f"  id={cid} content: {content[:300]}")
