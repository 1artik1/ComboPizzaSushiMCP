import os, re, json

path = r'C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_playwright_kaliforniya.html'
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Find product cards - look for specific patterns
# The classes 'cnt_item rL w100 h100 tbc vM' seem to be product items
# Let's extract text from these divs

# Find all cnt_item divs
cnt_items = re.findall(r'<div[^>]*class="[^"]*cnt_item[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
print('cnt_item divs:', len(cnt_items))
for i, item in enumerate(cnt_items[:5]):
    # Extract text
    texts = re.findall(r'>([^<]+)<', item)
    clean = ' | '.join([t.strip() for t in texts if t.strip() and 'http' not in t and 'BX' not in t])
    print('Item ' + str(i) + ': ' + clean[:200])
    print()

# Find price elements
price_classes = ['item_current_price', 'item_old_price', 'bx_item_detail_scu']
for pc in price_classes:
    prices = re.findall(r'<[^>]+class="[^"]*' + pc + r'[^"]*"[^>]*>(.*?)</[^>]+>', html_content, re.DOTALL)
    if prices:
        print(pc + ' prices:', len(prices))
        for p in prices[:3]:
            clean = re.sub(r'<[^>]+>', '', p).strip()
            print('  ' + clean)
        print()

# Find name elements
name_classes = ['item_section_name_gray', 'bx_item_section_name_gray']
for nc in name_classes:
    names = re.findall(r'<[^>]+class="[^"]*' + nc + r'[^"]*"[^>]*>(.*?)</[^>]+>', html_content, re.DOTALL)
    if names:
        print(nc + ' names:', len(names))
        for n in names[:5]:
            clean = re.sub(r'<[^>]+>', '', n).strip()
            print('  ' + clean)
        print()

# Look for category/section structure
section_names = re.findall(r'<[^>]+class="[^"]*name[^"]*"[^>]*>(.*?)</[^>]+>', html_content, re.DOTALL)
if section_names:
    print('name divs:', len(section_names))
    for n in section_names[:10]:
        clean = re.sub(r'<[^>]+>', '', n).strip()
        if clean and len(clean) > 3:
            print('  ' + clean)
