import re
with open(r'C:\Users\1artik1\AppData\Local\Temp\opencode\dodo_playwright.html', 'r', encoding='utf-8') as f:
    html = f.read()
print('Size:', len(html))

# Find script tags with JSON data
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print('Script tags:', len(scripts))
for i, s in enumerate(scripts[:5]):
    if len(s) > 100:
        first = s[:200]
        print('Script ' + str(i) + ': ' + first)
        print()

# Find API endpoint references
api_refs = re.findall(r'/api/v\d+/\S+', html)
if api_refs:
    print('API refs:', api_refs[:10])

# Find product-related elements
product_divs = re.findall(r'<div[^>]*class="[^"]*product[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
print('Product divs:', len(product_divs))

# Find price elements
price_divs = re.findall(r'<div[^>]*class="[^"]*price[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
print('Price divs:', len(price_divs))

# Find category/section structure
section_divs = re.findall(r'<div[^>]*class="[^"]*section[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
print('Section divs:', len(section_divs))

# Find all text content
texts = re.findall(r'>([^<]+)<', html)
unique_texts = set()
for t in texts:
    t = t.strip()
    if len(t) > 5 and len(t) < 100 and 'http' not in t and 'http://' not in t:
        unique_texts.add(t)

print('Unique short texts:', len(unique_texts))
for t in sorted(unique_texts)[:30]:
    print('  ' + t)
