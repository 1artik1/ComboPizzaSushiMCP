# -*- coding: utf-8 -*-
"""sushi_debug6.py — правильный парсер через BS4 DOM."""

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
print(f"HTML size: {len(html)}")

soup = BeautifulSoup(html, "html.parser")

# Find all div.tovar_small
tovar_small_divs = []
for d in soup.find_all("div", class_=True):
    cls = str(d.get("class") or [])
    if "tovar_small" in cls:
        tovar_small_divs.append(d)

print(f"\ntovar_small divs: {len(tovar_small_divs)}")

# Extract products
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
            
            # Find price from span.sale-price-current inside this card
            price = None
            price_span = card.find("span", class_=True)
            for ps in card.find_all("span", class_=True):
                ps_cls = str(ps.get("class") or [])
                if "sale-price-current" in ps_cls:
                    price_text = ps.get_text() or ""
                    digits = re.findall(r'\d+', price_text)
                    if digits:
                        price = int("".join(digits))
                    break
            
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
