# -*- coding: utf-8 -*-
"""sushi_debug5.py — отладка regex для цен sushi_time."""

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

chain_cfg = mcp_config.get_chain("sushi_time")
url = chain_cfg.get("url", "https://xn----8sbwgpzjf9b.xn--p1ai/Voronezh/")
html = http_client.fetch_html(url, chain_cfg)

# --- Test regex for price ---
# Current regex:
# id="price_preview_(\d+)"[^>]*>.*?<span[^>]*class="[^"]*sale-price-current[^"]*"[^>]*>(.*?)</span>
# Problem: .*? is non-greedy and may not match across nested spans

# Test on first price_preview
m = re.search(r'id="price_preview_(\d+)"[^>]*>(.*?)</span>', html, re.DOTALL)
if m:
    pid = m.group(1)
    text = m.group(2)
    print(f"First price_preview: id={pid}, text='{text[:200]}'")

# Test on first sale-price-current
m = re.search(r'class="[^"]*sale-price-current[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
if m:
    print(f"First sale-price-current: text='{m.group(1)[:200]}'")

# Check if sale-price-current is inside price_preview
idx = html.find('price_preview_')
if idx > 0:
    snippet = html[idx:idx+500]
    print(f"\nprice_preview snippet: {snippet[:500]}")

# Try different regex approach - find all price_preview spans and extract inner content
price_map = {}
for m in re.finditer(r'id="price_preview_(\d+)"[^>]*>(.*?)</span>', html, re.DOTALL):
    pid = m.group(1)
    text = m.group(2)
    digits = re.findall(r'\d+', text)
    if digits:
        price_map[pid] = int("".join(digits))

print(f"\nprice_map count: {len(price_map)}")
for pid, price in sorted(price_map.items())[:5]:
    print(f"  pid={pid} price={price}")
