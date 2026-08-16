# -*- coding: utf-8 -*-
"""ninja_deep_analysis.py — глубокий анализ ninja_food HTML."""

import sys
import re
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ninja_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_food_http.html"
with open(ninja_path, "r", encoding="utf-8", errors="replace") as f:
    ninja_html = f.read()

print(f"ninja HTML size: {len(ninja_html)}")

# Check for product cards in Bitrix format
# Look for common Bitrix product classes
product_classes = re.findall(r'class="[^"]*(?:item|product|catalog|offer)[^"]*"[^>]*>(.*?)(?:</div>\s*</div>\s*</div>|</div>\s*</div>\s*</div>)', ninja_html, re.DOTALL)
print(f"Potential product divs: {len(product_classes)}")

# Check for data attributes on product elements
data_attrs = re.findall(r'data-([^="]*?)="([^"]+)"', ninja_html)
print(f"\nAll data- attributes: {len(data_attrs)}")
unique_data = set(attr[0] for attr in data_attrs)
print(f"Unique data- attribute names: {len(unique_data)}")
for d in sorted(unique_data)[:20]:
    print(f"  data-{d}")

# Check for price in any form
price_patterns = re.findall(r'(?:price|cost|value)[^"<]*?(\d+)\s*[₽\u041f\u00a0]', ninja_html, re.IGNORECASE)
print(f"\nPrice patterns: {len(price_patterns)}")
for p in price_patterns[:10]:
    print(f"  price: {p}")

# Check for JSON in scripts
scripts = re.findall(r'<script[^>]*>(.*?)</script>', ninja_html, re.DOTALL)
print(f"\nScript blocks: {len(scripts)}")

# Look for product JSON
for i, script in enumerate(scripts):
    # Check if it contains product data
    if 'products' in script.lower() or 'offers' in script.lower() or 'catalog' in script.lower():
        print(f"\nScript {i} (first 500 chars):")
        print(script[:500])
        break

# Check for BX (Bitrix) data
bx_data = re.findall(r'bx_([^;]+?)\s*=', ninja_html)
print(f"\nBX variables: {len(bx_data)}")
unique_bx = set(bx_data)
print(f"Unique BX variables: {len(unique_bx)}")
for b in sorted(unique_bx)[:20]:
    print(f"  bx_{b}")

# Check for window.__INITIAL_STATE__ or similar
init_state = re.findall(r'window\.__INITIAL_STATE__\s*=\s*(.*?);', ninja_html, re.DOTALL)
print(f"\nwindow.__INITIAL_STATE__: {len(init_state)}")
for s in init_state[:2]:
    print(f"  {s[:300]}")

# Check for data-id values
data_ids = re.findall(r'data-id="([^"]+)"', ninja_html)
print(f"\ndata-id: {len(data_ids)}")
unique_ids = set(data_ids)
print(f"Unique data-id: {len(unique_ids)}")
for uid in sorted(unique_ids)[:10]:
    print(f"  id={uid}")

# Check for class names
class_names = re.findall(r'class="([^"]+)"', ninja_html)
print(f"\nAll classes: {len(class_names)}")
from collections import Counter
class_counts = Counter(class_names)
print(f"Top 20 classes: {class_counts.most_common(20)}")
