# -*- coding: utf-8 -*-
"""sushi_debug4.py — отладка парсера sushi_time v4."""

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

# --- Debug: Check tovar_small divs ---
tovar_small_divs = [d for d in soup.find_all("div", class_=True) if "tovar_small" in str(d.get("class") or [])]
print(f"\ntovar_small divs: {len(tovar_small_divs)}")

# Check first 3 tovar_small divs
for i, card in enumerate(tovar_small_divs[:3]):
    pid = card.get("data-id") or ""
    print(f"\nCard {i}: data-id='{pid}'")
    
    # Find <a> with data-title inside this card
    for a in card.find_all("a", attrs={"data-title": True}):
        title = a.get("data-title") or ""
        cat = a.get("data-category-name") or ""
        print(f"  a data-title='{title}' data-category-name='{cat}'")
        break
    
    # Find weight
    weight_spans = card.find_all("span", id=True)
    for ws in weight_spans:
        ws_id = ws.get("id") or ""
        if "vess_preview" in ws_id:
            wt_text = ws.get_text() or ""
            print(f"  weight span id='{ws_id}' text='{wt_text}'")
            break
    
    # Find price
    price_spans = card.find_all("span", class_=True)
    for ps in price_spans:
        ps_cls = str(ps.get("class") or [])
        if "sale-price-current" in ps_cls:
            price_text = ps.get_text() or ""
            print(f"  price span class='{ps_cls}' text='{price_text}'")
            break

# Check if any tovar_small div has an <a> with data-title
count_with_title = 0
for card in tovar_small_divs:
    for a in card.find_all("a", attrs={"data-title": True}):
        count_with_title += 1
        break

print(f"\ntovar_small divs with data-title <a>: {count_with_title}")
