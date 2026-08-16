# -*- coding: utf-8 -*-
"""sushi_debug11.py — проверка price_preview текста."""

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

# Find first price_preview div and check its text
for pd in soup.find_all("div", class_=True):
    pd_cls = str(pd.get("class") or [])
    if "price_preview" in pd_cls:
        text = pd.get_text() or ""
        print(f"price_preview text: '{text}'")
        # Find all prices with ₽
        for m in re.finditer(r'(\d+)\s*₽', text):
            print(f"  Found: {m.group(1)} ₽ at pos {m.start()}")
        break

# Check all price_preview divs for different patterns
patterns = {}
for pd in soup.find_all("div", class_=True):
    pd_cls = str(pd.get("class") or [])
    if "price_preview" in pd_cls:
        text = pd.get_text() or ""
        # Check what pattern the text matches
        if '+ a)' in text or '+b+' in text:
            patterns['js'] = patterns.get('js', 0) + 1
        elif '₽' in text:
            patterns['ruble'] = patterns.get('ruble', 0) + 1
        else:
            patterns['other'] = patterns.get('other', 0) + 1

print(f"\nPattern counts: {patterns}")

# Check a few price_preview divs
count = 0
for pd in soup.find_all("div", class_=True):
    pd_cls = str(pd.get("class") or [])
    if "price_preview" in pd_cls:
        count += 1
        if count <= 5:
            text = pd.get_text() or ""
            # Find all prices with ₽
            rubles = re.findall(r'(\d+)\s*₽', text)
            print(f"\nprice_preview #{count}: text='{text[:200]}'")
            print(f"  Ruble prices: {rubles}")
