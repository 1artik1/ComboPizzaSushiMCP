# -*- coding: utf-8 -*-
"""sushi_debug7.py — проверка структуры HTML для цен."""

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

# Find first tovar_small div
card = soup.find("div", class_=True)
while card:
    cls = str(card.get("class") or [])
    if "tovar_small" in cls:
        break
    card = card.find_next_sibling("div") if card.next_sibling else None
    # Try find_all approach
    for d in soup.find_all("div", class_=True):
        if "tovar_small" in str(d.get("class") or []):
            card = d
            break

print(f"First tovar_small: data-id='{card.get('data-id')}'")
print(f"HTML snippet around card:")

# Find the HTML for this card
pid = card.get("data-id", "")
# Find by data-id in raw HTML
idx = html.find(f'data-id="{pid}"')
if idx > 0:
    snippet = html[idx:idx+2000]
    print(snippet[:2000])
else:
    print("Not found by data-id, trying class-based search")

# Check all sale-price-current spans
spans = soup.find_all("span", class_=True)
sale_price_count = 0
for s in spans:
    cls = str(s.get("class") or [])
    if "sale-price-current" in cls:
        sale_price_count += 1
        if sale_price_count <= 3:
            text = s.get_text() or ""
            parent = s.parent
            p_cls = str(parent.get("class") or []) if parent else "None"
            print(f"\nsale-price-current: text='{text}' parent class='{p_cls}'")

print(f"\ntotal sale-price-current spans: {sale_price_count}")

# Check if there are price_preview spans with actual prices (not JS)
price_preview_count = 0
for d in soup.find_all("div", class_=True):
    cls = str(d.get("class") or [])
    if "price_preview" in cls:
        price_preview_count += 1
        if price_preview_count <= 3:
            text = d.get_text() or ""
            print(f"\nprice_preview div: class='{cls}' text='{text[:200]}'")

print(f"\ntotal price_preview divs: {price_preview_count}")
