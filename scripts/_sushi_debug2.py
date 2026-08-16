# -*- coding: utf-8 -*-
"""sushi_debug2.py — отладка парсера sushi_time v2."""

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

# --- Debug: Check linknoactive class ---
linknoactive_a = soup.find_all("a", class_=True)
print(f"\nAll <a> tags with class: {len(linknoactive_a)}")

# Check first few
for a in linknoactive_a[:5]:
    a_cls = str(a.get("class") or [])
    print(f"  a class='{a_cls}' data-title='{a.get('data-title')}'")
    parent = a.find_parent("div", class_=True)
    if parent:
        p_cls = str(parent.get("class") or [])
        print(f"    parent div class='{p_cls}' data-id='{parent.get('data-id')}'")

# Check if any <a> has linknoactive in its class
linknoactive_count = 0
for a in soup.find_all("a", class_=True):
    a_cls = str(a.get("class") or [])
    if "linknoactive" in a_cls:
        linknoactive_count += 1
        if linknoactive_count <= 3:
            parent = a.find_parent("div", class_=True)
            if parent:
                p_cls = str(parent.get("class") or [])
                print(f"\n  linknoactive found: class='{a_cls}' data-title='{a.get('data-title')}'")
                print(f"    parent div class='{p_cls}' data-id='{parent.get('data-id')}'")

print(f"\nlinknoactive <a> count: {linknoactive_count}")

# Check if any <a> has data-title
data_title_a = soup.find_all("a", attrs={"data-title": True})
print(f"<a> with data-title: {len(data_title_a)}")
for a in data_title_a[:3]:
    print(f"  data-title='{a.get('data-title')}' class='{a.get('class')}'")

# Check if any <a> has data-category-name
data_cat_a = soup.find_all("a", attrs={"data-category-name": True})
print(f"<a> with data-category-name: {len(data_cat_a)}")
for a in data_cat_a[:3]:
    print(f"  data-category-name='{a.get('data-category-name')}' class='{a.get('class')}'")

# Check if parent div has tovar_small
for a in data_title_a[:3]:
    parent = a.find_parent("div", class_=True)
    if parent:
        p_cls = str(parent.get("class") or [])
        print(f"\n  Parent of data-title <a>: class='{p_cls}' data-id='{parent.get('data-id')}'")
        if "tovar_small" in p_cls:
            print(f"    -> This is a tovar_small card!")
