# -*- coding: utf-8 -*-
"""sushi_price_finder.py — ищем цены в sushi_time HTML."""

import sys
import re
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from bs4 import BeautifulSoup

html_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\sushi_time_http.html"
with open(html_path, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find a div with itemtype="http://schema.org/Product"
product_divs = soup.find_all("div", {"itemtype": re.compile(r".*schema.*Product.*")})
print(f"Schema.org Product divs: {len(product_divs)}")

for i, div in enumerate(product_divs[:3]):
    print(f"\n--- Product div {i} ---")
    print(f"  itemtype: {div.get('itemtype')}")
    print(f"  class: {div.get('class')}")
    print(f"  data-id: {div.get('data-id')}")
    print(f"  data-title: {div.get('data-title')}")
    
    # Find price element
    price_el = div.find(class_=re.compile(r".*price.*"))
    if price_el:
        print(f"  price element class: {price_el.get('class')}")
        pt = price_el.get_text()
        print(f"  price text: '{pt}'")
        print(f"  price itemprop: {price_el.get('itemprop')}")
        print(f"  price data-price: {price_el.get('data-price')}")
    
    # Find all spans with itemprop
    for sp in div.find_all("span", {"itemprop": True}):
        stext = sp.get_text()
        print(f"  span itemprop='{sp.get('itemprop')}' class={sp.get('class')} text='{stext}'")
    
    # Find all elements with data-price
    for el in div.find_all(attrs={"data-price": True}):
        print(f"  el data-price='{el.get('data-price')}' tag={el.name}")

# Also check for meta tags with prices
meta_prices = soup.find_all("meta", {"itemprop": "price"})
print(f"\nMeta price tags: {len(meta_prices)}")
for mp in meta_prices[:5]:
    print(f"  content: {mp.get('content')}")

# Check for JSON-LD in script tags more carefully
scripts = soup.find_all("script", {"type": "application/ld+json"})
print(f"\nJSON-LD scripts: {len(scripts)}")
for i, s in enumerate(scripts):
    text = s.get_text()
    print(f"  Script {i}: {text[:300]}")

# Check for any element with itemprop="price" anywhere
all_price_items = soup.find_all(attrs={"itemprop": "price"})
print(f"\nAll elements with itemprop='price': {len(all_price_items)}")
for p in all_price_items[:10]:
    pt = p.get_text()
    print(f"  {p.name} class={p.get('class')} text='{pt}'")

# Check for data-price attributes on any element
all_data_prices = soup.find_all(attrs={"data-price": True})
print(f"\nAll elements with data-price: {len(all_data_prices)}")
for dp in all_data_prices[:10]:
    print(f"  {dp.name} class={dp.get('class')} data-price='{dp.get('data-price')}'")

# Check for span with class containing 'price_preview'
price_previews = soup.find_all("span", class_=re.compile(r".*price_preview.*"))
print(f"\nElements with price_preview class: {len(price_previews)}")
for pp in price_previews[:10]:
    pt = pp.get_text()
    print(f"  class={pp.get('class')} text='{pt}' id={pp.get('id')}")

# Check for .priceRaw class
price_raws = soup.find_all("span", class_=re.compile(r".*priceRaw.*"))
print(f"\nElements with priceRaw class: {len(price_raws)}")
for pr in price_raws[:10]:
    pt = pr.get_text()
    print(f"  class={pr.get('class')} text='{pt}' data-price='{pr.get('data-price')}'")
