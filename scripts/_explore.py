import os, re, json

path = r'C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_playwright_kaliforniya.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()
print('Size:', len(html))

# Look for product data patterns
# Find all <div> tags with class containing 'product' or 'card' or 'item'
for cls_keyword in ['product', 'card', 'item', 'catalog', 'dish', 'food']:
    pat = r'<[^>]+class=[\"'][^\"' + cls_keyword + r'\"']' + cls_keyword + r'[^\"' + cls_keyword + r']*[\"'][^>]*>'
    matches = re.findall(pat, html)
    if matches:
        print(cls_keyword + ' divs:', len(matches))
        for m in matches[:2]:
            print('  ', m[:200])
        print()
