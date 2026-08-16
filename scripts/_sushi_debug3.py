# -*- coding: utf-8 -*-
"""sushi_debug3.py — отладка парсера sushi_time v3."""

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

# Find a <a> with data-title and trace up the hierarchy
for a in soup.find_all("a", attrs={"data-title": True}):
    title = a.get("data-title")
    if not title or title == "Дружба":
        print(f"\n<a data-title='{title}'> hierarchy:")
        parent = a.parent
        depth = 0
        while parent and depth < 5:
            p_cls = str(parent.get("class") or [])
            p_id = parent.get("data-id") or ""
            print(f"  depth={depth}: {parent.name} class='{p_cls}' data-id='{p_id}'")
            parent = parent.parent
            depth += 1
        break

# Check if there's a div.tovar_small that contains the <a> with data-title
tovar_small_divs = soup.find_all("div", class_=True)
tovar_small_count = 0
for d in tovar_small_divs:
    d_cls = str(d.get("class") or [])
    if "tovar_small" in d_cls:
        tovar_small_count += 1
        # Check if it contains an <a> with data-title
        a_with_title = d.find("a", attrs={"data-title": True})
        if a_with_title:
            print(f"\ntovar_small div with data-title <a>:")
            print(f"  data-id='{d.get('data-id')}'")
            print(f"  data-title='{a_with_title.get('data-title')}'")
            print(f"  data-category-name='{a_with_title.get('data-category-name')}'")
            tovar_small_count += 1
            if tovar_small_count > 3:
                break

print(f"\ntovar_small divs: {len([d for d in tovar_small_divs if 'tovar_small' in str(d.get('class') or [])])}")
