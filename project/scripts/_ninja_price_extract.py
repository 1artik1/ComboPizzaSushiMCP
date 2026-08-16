# -*- coding: utf-8 -*-
"""ninja_price_extract.py — извлекаем цены из ninja_food HTML."""

import sys
import re
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

ninja_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_food_http.html"
with open(ninja_path, "r", encoding="utf-8", errors="replace") as f:
    ninja_html = f.read()

# Find a product card in the HTML
# Look for catalog_element box
card_match = re.search(r'(<div[^>]*class="[^"]*catalog_element[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>)', ninja_html, re.DOTALL)
if card_match:
    print(f"First product card (first 800 chars):")
    print(card_match.group(1)[:800])

# Check for price structure
price_match = re.search(r'class="price"[^>]*>(.*?)</div>', ninja_html, re.DOTALL)
if price_match:
    print(f"\nPrice div: {price_match.group(1)[:300]}")

# Check for new_price
new_price_match = re.search(r'class="new_price"[^>]*>(.*?)</div>', ninja_html, re.DOTALL)
if new_price_match:
    print(f"\nNew price: {new_price_match.group(1)[:300]}")

# Check for old_price
old_price_match = re.search(r'class="old_price"[^>]*>(.*?)</div>', ninja_html, re.DOTALL)
if old_price_match:
    print(f"\nOld price: {old_price_match.group(1)[:300]}")

# Check for name
name_match = re.search(r'class="name"[^>]*>(.*?)</div>', ninja_html, re.DOTALL)
if name_match:
    print(f"\nName: {name_match.group(1)[:300]}")

# Check for data-offers
offers_match = re.search(r'data-offers="([^"]*)"', ninja_html)
if offers_match:
    print(f"\ndata-offers: {offers_match.group(1)[:300]}")

# Check for all data-offers
all_offers = re.findall(r'data-offers="([^"]*)"', ninja_html)
print(f"\nAll data-offers: {len(all_offers)}")
for o in all_offers[:5]:
    print(f"  {o[:200]}")

# Check for data-url
all_urls = re.findall(r'data-url="([^"]*)"', ninja_html)
print(f"\nAll data-url: {len(all_urls)}")
for u in all_urls[:5]:
    print(f"  {u}")
