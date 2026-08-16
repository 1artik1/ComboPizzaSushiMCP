# -*- coding: utf-8 -*-
"""sushi_final_price_check.py — финальная проверка цен."""

import sys
import re
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

html_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\sushi_time_http.html"
with open(html_path, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

# The price_preview spans contain nested .sale-price-current
# Let's extract them properly
price_preview_ids = re.findall(r'id="price_preview_(\d+)"[^>]*>(.*?)</span>\s*</span>', html, re.DOTALL)
print(f"price_preview with id: {len(price_preview_ids)}")

# Extract price from each
for pid, content in price_preview_ids[:5]:
    # Find sale-price-current inside
    sale_match = re.search(r'sale-price-current[^>]*>([^<]*)', content)
    if sale_match:
        price_text = sale_match.group(1).strip()
        # Extract digits
        digits = re.findall(r'\d+', price_text)
        if digits:
            price = int(digits[0])
            print(f"  id={pid} price_text='{price_text}' price={price}")

# Also check for weight
weight_spans = re.findall(r'id="vess_preview_(\d+)"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\nvess_preview with id: {len(weight_spans)}")
for wid, content in weight_spans[:5]:
    # Extract weight
    weight_match = re.search(r'(\d+)\s*[гг]', content)
    if weight_match:
        weight = int(weight_match.group(1))
        print(f"  id={wid} weight={weight}")

# Check for data-title
titles = re.findall(r'data-title="([^"]*)"', html)
print(f"\ndata-title: {len(titles)}")

# Check for data-category-name
cats = re.findall(r'data-category-name="([^"]*)"', html)
print(f"data-category-name: {len(cats)}")

# Now let's check the ninja_food HTML
print("\n\n=== NINJA FOOD ===")
ninja_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_food_http.html"
with open(ninja_path, "r", encoding="utf-8", errors="replace") as f:
    ninja_html = f.read()

print(f"ninja HTML size: {len(ninja_html)}")

# Check for product cards
product_divs = re.findall(r'<div[^>]*class="[^"]*product[^"]*"[^>]*>(.*?)</div>', ninja_html, re.DOTALL)
print(f"Product divs: {len(product_divs)}")

# Check for data attributes
data_ids = re.findall(r'data-id="([^"]*)"', ninja_html)
print(f"data-id: {len(data_ids)}")

# Check for price
prices = re.findall(r'data-price="([^"]*)"', ninja_html)
print(f"data-price: {len(prices)}")

# Check for meta tags
meta_prices = re.findall(r'<meta[^>]*itemprop="price"[^>]*content="([^"]*)"[^>]*>', ninja_html)
print(f"Meta price: {len(meta_prices)}")

# Check for script blocks
scripts = re.findall(r'<script[^>]*>(.*?)</script>', ninja_html, re.DOTALL)
print(f"Script blocks: {len(scripts)}")

# Check for JSON in scripts
for i, script in enumerate(scripts):
    if 'products' in script.lower() or 'price' in script.lower():
        print(f"\nScript {i} has product/price data:")
        print(script[:300])
        break
