# Debug sushi_time HTML parsing
import sys, os, codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

_project_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_project_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from combo_mcp import http_client
from combo_mcp import config as mcp_config
from bs4 import BeautifulSoup
import re

# Fetch HTML
chain_cfg = mcp_config.get_chain("sushi_time")
url = chain_cfg.get("url", "https://xn----8sbwgpzjf9b.xn--p1ai/Voronezh/")
html = http_client.fetch_html(url, chain_cfg)
print("URL:", url)
print("HTML length:", len(html) if html else 0)

if html:
    soup = BeautifulSoup(html, "html.parser")
    
    # Check data-id elements
    data_ids = soup.find_all(attrs={"data-id": True})
    print("data-id elements:", len(data_ids))
    
    # Check data-title elements
    data_titles = soup.find_all(attrs={"data-title": True})
    print("data-title elements:", len(data_titles))
    
    # Check data-category-name elements
    data_cats = soup.find_all(attrs={"data-category-name": True})
    print("data-category-name elements:", len(data_cats))
    
    # Check vess_preview spans
    vess_spans = soup.find_all("span", class_=True)
    vess_count = 0
    for s in vess_spans:
        cls = s.get("class") or []
        for c in cls:
            if "vess_preview" in str(c):
                vess_count += 1
                break
    print("vess_preview spans:", vess_count)
    
    # Check sale-price spans
    sale_count = 0
    for s in vess_spans:
        cls = s.get("class") or []
        for c in cls:
            if "sale-price" in str(c):
                sale_count += 1
                break
    print("sale-price spans:", sale_count)
    
    # Check if data attributes are on the same elements
    if data_ids:
        first = data_ids[0]
        print("First data-id element:", first.name, first.get("class"), first.attrs)
        print("First data-id text:", first.get_text()[:100])
    
    if data_titles:
        first = data_titles[0]
        print("First data-title element:", first.name, first.get("class"), first.attrs)
        print("First data-title text:", first.get_text()[:100])
    
    # Check if data-id and data-title are on the same element
    for tag in data_ids[:5]:
        title = tag.get("data-title")
        cat = tag.get("data-category-name")
        if title or cat:
            print(f"  data-id={tag.get('data-id')} title={title} cat={cat}")
    
    # Check if there are nested elements
    for tag in data_ids[:3]:
        children = tag.find_all(True)
        print(f"  data-id={tag.get('data-id')} children: {len(children)}")
        for child in children[:3]:
            print(f"    {child.name} class={child.get('class')} title={child.get('data-title')}")
