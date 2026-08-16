# -*- coding: utf-8 -*-
"""sushi_debug8.py — парсер через price_preview div."""

import sys
import re
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

import os
_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from combo_mcp import http_client
from combo_mcp import config as mcp_config
from bs4 import BeautifulSoup

chain_cfg = mcp_config.get_chain("sushi_time")
url = chain_cfg.get("url", "https://xn----8sbwgpzjf9b.xn--p1ai/Voronezh/")
html = http_client.fetch_html(url, chain_cfg)

soup = BeautifulSoup(html, "html.parser")

# Find all price_preview divs and extract prices
price_preview_divs = [d for d in soup.find_all("div", class_=True) if "price_preview" in str(d.get("class") or [])]
print(f"price_preview divs: {len(price_preview_divs)}")

# Extract prices from price_preview divs
price_map = {}
for d in price_preview_divs:
    pid = d.get("data-id") or ""
    text = d.get_text() or ""
    # Find all prices like "650 ₽" or "1 300 ₽"
    digits = re.findall(r'\d+', text)
    if digits:
        # First number is the price
        price_map[pid] = int(digits[0])

print(f"price_map: {len(price_map)}")
for pid, price in sorted(price_map.items())[:5]:
    print(f"  pid={pid} price={price}")

# Now build products
tovar_small_divs = [d for d in soup.find_all("div", class_=True) if "tovar_small" in str(d.get("class") or [])]
print(f"\ntovar_small divs: {len(tovar_small_divs)}")

products = []
for card in tovar_small_divs:
    pid = card.get("data-id") or ""
    if not pid:
        continue
    
    # Find <a> with data-title inside this card
    for a in card.find_all("a", attrs={"data-title": True}):
        title = a.get("data-title") or ""
        cat = a.get("data-category-name") or ""
        if isinstance(title, str) and title.strip():
            name = title.strip()
            category = cat.strip() if isinstance(cat, str) and cat.strip() else "Роллы/Суши"
            
            # Find weight from span#vess_preview_<pid>
            weight = None
            weight_span = card.find("span", id=f"vess_preview_{pid}")
            if weight_span:
                wt_text = weight_span.get_text() or ""
                m = re.search(r"(\d+)\s*[гг]", wt_text)
                if m:
                    weight = int(m.group(1))
            
            # Find price from price_map
            price = price_map.get(pid)
            
            products.append({
                "pid": pid,
                "name": name,
                "category": category,
                "weight": weight,
                "price": price,
            })
            break

print(f"\nProducts extracted: {len(products)}")
for p in products[:5]:
    print(f"  {p['name']} | {p['weight']}g | {p['price']}rub | {p['category']}")

# Count valid (price>0)
valid = [p for p in products if p['price'] is not None and p['price'] > 0]
print(f"\nValid (price>0): {len(valid)}")
for p in valid[:5]:
    print(f"  {p['name']} | {p['weight']}g | {p['price']}rub | {p['category']}")
