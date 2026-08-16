# -*- coding: utf-8 -*-
"""sushi_debug.py — отладка парсера sushi_time."""

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

# --- Build id -> (name, category) map ---
id_info = {}
for a in soup.find_all("a", class_=True):
    a_cls = a.get("class") or []
    if "linknoactive" not in a_cls:
        continue
    parent = a.find_parent("div", class_=True)
    if parent:
        p_cls = parent.get("class") or []
        if "tovar_small" in p_cls:
            pid = parent.get("data-id") or ""
            if pid:
                title = a.get("data-title") or ""
                cat = a.get("data-category-name") or ""
                if isinstance(title, str) and title.strip():
                    id_info[pid] = {
                        "name": title.strip(),
                        "category": cat.strip() if isinstance(cat, str) and cat.strip() else "Роллы/Суши",
                    }

print(f"id_info count: {len(id_info)}")
for pid, info in list(id_info.items())[:3]:
    print(f"  id={pid} name='{info['name']}' category='{info['category']}'")

# --- Extract weight ---
weight_map = {}
for pid, wt_text in re.findall(
    r'id="vess_preview_(\d+)"[^>]*>(.*?)</span>', html, re.DOTALL
):
    m = re.search(r"(\d+)\s*[гг]", wt_text)
    if m:
        weight_map[pid] = int(m.group(1))

print(f"weight_map count: {len(weight_map)}")
for pid, wt in list(weight_map.items())[:3]:
    print(f"  id={pid} weight={wt}")

# --- Extract price ---
price_map = {}
# Check if the regex pattern matches anything
pattern = r'id="price_preview_(\d+)"[^>]*>.*?<span[^>]*class="[^"]*sale-price-current[^"]*"[^>]*>(.*?)</span>'
matches = re.findall(pattern, html, re.DOTALL)
print(f"price regex matches: {len(matches)}")
for pid, price_text in matches[:3]:
    digits = re.findall(r"\d+", price_text)
    if digits:
        price_map[pid] = int(digits[0])
        print(f"  id={pid} price_text='{price_text[:50]}' price={price_map[pid]}")

# If no matches, try alternative pattern
if not matches:
    print("No matches with primary pattern, trying alternatives...")
    # Try simpler pattern
    simple_pattern = r'price_preview_(\d+).*?sale-price-current.*?>([^<]+)'
    simple_matches = re.findall(simple_pattern, html, re.DOTALL)
    print(f"Simple pattern matches: {len(simple_matches)}")
    for pid, price_text in simple_matches[:3]:
        digits = re.findall(r"\d+", price_text)
        if digits:
            price_map[pid] = int(digits[0])
            print(f"  id={pid} price_text='{price_text[:50]}' price={price_map[pid]}")

# --- Build products ---
products = []
for pid, info in id_info.items():
    name = info["name"]
    category = info["category"]
    weight = weight_map.get(pid)
    price = price_map.get(pid)

    print(f"  id={pid} name='{name}' weight={weight} price={price}")

    if price is None:
        continue

    products.append({
        "name": name,
        "weight_g": weight,
        "price_rub": price,
        "is_from_price": False,
        "description": name,
        "category": category,
        "product_url": "",
    })

print(f"\nTotal products: {len(products)}")
