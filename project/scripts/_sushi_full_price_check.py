# -*- coding: utf-8 -*-
"""sushi_full_price_check.py — полный анализ цен в sushi_time."""

import sys
import re
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

html_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\sushi_time_http.html"
with open(html_path, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

# 1. Check for data-menu-stop-offers (might contain prices)
offers_match = re.search(r'data-menu-stop-offers="(\[.*?\])"', html)
if offers_match:
    print(f"data-menu-stop-offers: {offers_match.group(1)[:300]}")

# 2. Check for any JSON data in script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nScript blocks: {len(scripts)}")

# Look for product data in scripts
for i, script in enumerate(scripts):
    # Check if it contains price data
    if re.search(r'"price".*:".*\d', script, re.IGNORECASE):
        print(f"\nScript {i} has price data:")
        print(script[:500])
        break

# 3. Check for data attributes on the product card div itself
card_divs = re.findall(r'div[^>]*class="[^"]*tovar_small[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
print(f"\nProduct card divs: {len(card_divs)}")

if card_divs:
    print(f"\nFirst card div (first 500 chars):")
    print(card_divs[0][:500])

# 4. Check for .price_preview in the HTML more carefully
price_preview_matches = re.findall(r'class="[^"]*price_preview[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\nprice_preview spans: {len(price_preview_matches)}")
for pp in price_preview_matches[:5]:
    clean = re.sub(r'\s+', '', pp).strip()
    print(f"  price_preview: '{clean}'")

# 5. Check for .priceBlock
price_block_matches = re.findall(r'class="[^"]*priceBlock[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\npriceBlock spans: {len(price_block_matches)}")
for pb in price_block_matches[:5]:
    clean = re.sub(r'\s+', '', pb).strip()
    print(f"  priceBlock: '{clean}'")

# 6. Check for .setPrice_preview
set_price_matches = re.findall(r'class="[^"]*setPrice_preview[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\nsetPrice_preview spans: {len(set_price_matches)}")
for sp in set_price_matches[:5]:
    clean = re.sub(r'\s+', '', sp).strip()
    print(f"  setPrice_preview: '{clean}'")

# 7. Check for any element with data-price
data_price_matches = re.findall(r'data-price="([^"]+)"', html)
print(f"\ndata-price attributes: {len(data_price_matches)}")
for dp in data_price_matches[:5]:
    print(f"  data-price: '{dp}'")

# 8. Check for data-price on any element (not just attributes)
data_price_all = re.findall(r'(\w+)[^>]*data-price="([^"]+)"', html)
print(f"\nAll elements with data-price: {len(data_price_all)}")
for tag, dp in data_price_all[:5]:
    print(f"  {tag} data-price: '{dp}'")

# 9. Check for price in meta tags with different structure
meta_prices = re.findall(r'<meta[^>]*itemprop="price"[^>]*content="([^"]*)"[^>]*>', html)
print(f"\nMeta price raw: {len(meta_prices)}")
for mp in meta_prices[:5]:
    print(f"  content: '{mp}'")

# 10. Check for priceRaw
price_raw = re.findall(r'class="[^"]*priceRaw[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\npriceRaw spans: {len(price_raw)}")
for pr in price_raw[:5]:
    clean = re.sub(r'\s+', '', pr).strip()
    print(f"  priceRaw: '{clean}'")

# 11. Check for price-current
price_current = re.findall(r'class="[^"]*price[-_]current[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\nprice-current spans: {len(price_current)}")
for pc in price_current[:5]:
    clean = re.sub(r'\s+', '', pc).strip()
    print(f"  price-current: '{clean}'")

# 12. Check for oldPrice
old_price = re.findall(r'class="[^"]*oldPrice[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\noldPrice spans: {len(old_price)}")
for op in old_price[:5]:
    clean = re.sub(r'\s+', '', op).strip()
    print(f"  oldPrice: '{clean}'")

# 13. Check for dostavka_price
dostavka_price = re.findall(r'class="[^"]*dostavka_price[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
print(f"\ndostavka_price spans: {len(dostavka_price)}")
for dp in dostavka_price[:5]:
    clean = re.sub(r'\s+', '', dp).strip()
    print(f"  dostavka_price: '{clean}'")
