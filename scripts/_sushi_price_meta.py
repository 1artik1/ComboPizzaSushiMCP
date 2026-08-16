# -*- coding: utf-8 -*-
"""sushi_price_meta.py — проверяем meta теги с itemprop='price'."""

import sys
import re
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from bs4 import BeautifulSoup

html_path = r"C:\Users\1artik1\AppData\Local\Temp\opencode\sushi_time_http.html"
with open(html_path, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Check meta tags more carefully
meta_prices = soup.find_all("meta", {"itemprop": "price"})
print(f"Meta price tags: {len(meta_prices)}")

# Look at the raw HTML around a product card
import re as regex

# Find a product card in raw HTML
card_match = regex.search(r'(data-id="1643".*?)(</div>\s*</div>\s*</div>)', html, regex.DOTALL)
if card_match:
    print("\n--- Raw HTML around data-id=1643 ---")
    print(card_match.group(1)[:1000])

# Check meta tags in raw HTML
meta_matches = regex.findall(r'<meta[^>]*itemprop="price"[^>]*content="([^"]*)"[^>]*>', html)
print(f"\nMeta price raw matches: {len(meta_matches)}")
for m in meta_matches[:5]:
    print(f"  content='{m}'")

# Check for meta tags with different attributes
meta_all = soup.find_all("meta", {"itemprop": True})
print(f"\nAll meta with itemprop: {len(meta_all)}")
for m in meta_all[:5]:
    print(f"  itemprop='{m.get('itemprop')}' content='{m.get('content')}'")

# Check the actual price span structure in raw HTML
price_match = regex.search(r'(<span[^>]*class="[^"]*price_preview[^"]*"[^>]*>.*?</span>)', html, regex.DOTALL)
if price_match:
    print(f"\nRaw price_preview span: {price_match.group(1)[:300]}")

# Check for nested structure
price_match2 = regex.search(r'(<span[^>]*class="[^"]*price_preview[^"]*"[^>]*>.*?</span>)', html, regex.DOTALL)
if price_match2:
    print(f"\nFull price_preview: {price_match2.group(1)}")

# Check for .priceRaw
price_raw_match = regex.search(r'(<span[^>]*class="[^"]*priceRaw[^"]*"[^>]*>.*?</span>)', html, regex.DOTALL)
if price_raw_match:
    print(f"\npriceRaw: {price_raw_match.group(1)}")

# Check for .pricePreview (uppercase P)
price_preview_match = regex.search(r'(<span[^>]*class="[^"]*pricePreview[^"]*"[^>]*>.*?</span>)', html, regex.DOTALL)
if price_preview_match:
    print(f"\npricePreview: {price_preview_match.group(1)}")

# Check for .setPrice_preview
set_price_match = regex.search(r'(<span[^>]*class="[^"]*setPrice_preview[^"]*"[^>]*>.*?</span>)', html, regex.DOTALL)
if set_price_match:
    print(f"\nsetPrice_preview: {set_price_match.group(1)}")

# Check for .priceBlock
price_block_match = regex.search(r'(<span[^>]*class="[^"]*priceBlock[^"]*"[^>]*>.*?</span>)', html, regex.DOTALL)
if price_block_match:
    print(f"\npriceBlock: {price_block_match.group(1)}")

# Check for data-price in any element
dp_match = regex.search(r'(<[^>]+data-price="([^"]+)"[^>]*>.*?</[^>]+>)', html, regex.DOTALL)
if dp_match:
    print(f"\ndata-price element: {dp_match.group(1)[:300]}")

# Check for .price-current or similar
price_current_match = regex.search(r'(<span[^>]*class="[^"]*price[-_]current[^"]*"[^>]*>.*?</span>)', html, regex.DOTALL)
if price_current_match:
    print(f"\nprice-current: {price_current_match.group(1)[:300]}")
