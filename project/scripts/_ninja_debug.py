# -*- coding: utf-8 -*-
"""ninja_debug.py — отладка парсера ninja_food."""

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

chain_cfg = mcp_config.get_chain("ninja_food")
url = chain_cfg.get("url", "https://ninjafood.su/")
html = http_client.fetch_html(url, chain_cfg)
print(f"HTML size: {len(html)}")

soup = BeautifulSoup(html, "html.parser")

# Find product cards
cards = soup.find_all("div", class_=True)
product_cards = [c for c in cards if "catalog_element" in str(c.get("class") or [])]
print(f"Product cards: {len(product_cards)}")

# Check first card
if product_cards:
    card = product_cards[0]
    print(f"\nFirst card class: {card.get('class')}")
    print(f"First card data-id: {card.get('data-id')}")
    print(f"First card data-offers: {card.get('data-offers')}")
    
    # Find name
    for el in card.find_all(["a", "span"], class_=True):
        el_cls = str(el.get("class") or [])
        if "name" in el_cls or "often_ordered_element_name" in el_cls:
            t = el.get_text().strip()
            print(f"  Found name element: class={el_cls} text='{t}'")
    
    # Find price
    for el in card.find_all("span", class_=True):
        el_cls = str(el.get("class") or [])
        if "new_price" in el_cls:
            t = el.get_text() or ""
            print(f"  Found price element: class={el_cls} text='{t}'")

    # Print full card HTML
    print(f"\nFirst card HTML (first 500 chars):")
    print(str(card)[:500])
