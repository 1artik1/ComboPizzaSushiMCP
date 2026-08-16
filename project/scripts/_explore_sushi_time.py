import re
with open(r'C:\Users\1artik1\AppData\Local\Temp\opencode\sushi_time_http.html', 'r', encoding='utf-8') as f:
    html = f.read()
print('Size:', len(html))

# Find product-related patterns
for attr in ['data-title', 'data-category-name', 'data-id', 'data-price', 'data-weight']:
    pat = r'\b' + attr + r'=[^\s>]+\s*'
    matches = re.findall(pat, html)
    if matches:
        print(attr + ' found:', len(matches))
    else:
        print(attr + ' NOT found')

# Find span patterns using different approach
import re
# Find all class attributes
class_pattern = r'class="([^"]*)"'
classes = re.findall(class_pattern, html)
from collections import Counter
class_counts = Counter(classes)
print('Top 20 classes:', class_counts.most_common(20))

# Find span with vess_preview
vess_matches = re.findall(r'<span[^>]*vess[^>]*>(.*?)</span>', html, re.DOTALL)
print('vess span matches:', len(vess_matches))
for m in vess_matches[:3]:
    clean = re.sub(r'<[^>]+>', '', m).strip()
    if clean:
        print('  ' + clean[:100])

# Find span with sale-price
sale_matches = re.findall(r'<span[^>]*sale-price[^>]*>(.*?)</span>', html, re.DOTALL)
print('sale-price span matches:', len(sale_matches))
for m in sale_matches[:3]:
    clean = re.sub(r'<[^>]+>', '', m).strip()
    if clean:
        print('  ' + clean[:100])

# Find product titles in h2, h3, etc.
for tag in ['h2', 'h3', 'h4']:
    matches = re.findall(r'<' + tag + r'[^>]*>(.*?)</' + tag + r'>', html, re.DOTALL)
    if matches:
        print(tag + ' matches:', len(matches))
        for m in matches[:5]:
            clean = re.sub(r'<[^>]+>', '', m).strip()
            if clean and len(clean) > 3:
                print('  ' + clean[:80])
        print()
