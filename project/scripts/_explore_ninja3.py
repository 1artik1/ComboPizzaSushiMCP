import os, re, json

path = r'C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_playwright_kaliforniya.html'
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

out_lines = []

# Find all cnt_item divs
cnt_items = re.findall(r'<div[^>]*class="[^"]*cnt_item[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
out_lines.append('cnt_item divs: ' + str(len(cnt_items)))

# Find price elements
for pc in ['item_current_price', 'item_old_price', 'bx_item_detail_scu']:
    prices = re.findall(r'<[^>]+class="[^"]*' + pc + r'[^"]*"[^>]*>(.*?)</[^>]+>', html_content, re.DOTALL)
    if prices:
        out_lines.append(pc + ' prices: ' + str(len(prices)))
        for p in prices[:5]:
            clean = re.sub(r'<[^>]+>', '', p).strip()
            out_lines.append('  ' + clean[:80])
        out_lines.append('')

# Find name elements
for nc in ['item_section_name_gray', 'bx_item_section_name_gray']:
    names = re.findall(r'<[^>]+class="[^"]*' + nc + r'[^"]*"[^>]*>(.*?)</[^>]+>', html_content, re.DOTALL)
    if names:
        out_lines.append(nc + ' names: ' + str(len(names)))
        for n in names[:10]:
            clean = re.sub(r'<[^>]+>', '', n).strip()
            out_lines.append('  ' + clean[:80])
        out_lines.append('')

# Find category/section structure
section_names = re.findall(r'<[^>]+class="[^"]*name[^"]*"[^>]*>(.*?)</[^>]+>', html_content, re.DOTALL)
if section_names:
    out_lines.append('name divs: ' + str(len(section_names)))
    for n in section_names[:10]:
        clean = re.sub(r'<[^>]+>', '', n).strip()
        if clean and len(clean) > 3:
            out_lines.append('  ' + clean)

# Also look at the HTML around product cards
# Find divs with class containing 'bx_slide'
slide_divs = re.findall(r'<div[^>]+class="[^"]*bx_slide[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
out_lines.append('bx_slide divs: ' + str(len(slide_divs)))
for i, s in enumerate(slide_divs[:2]):
    texts = re.findall(r'>([^<]+)<', s)
    clean = ' | '.join([t.strip() for t in texts if t.strip() and len(t.strip()) > 2])
    out_lines.append('Slide ' + str(i) + ': ' + clean[:200])
    out_lines.append('')

# Look for the full page structure - find section headings
section_divs = re.findall(r'<div[^>]+class="[^"]*section[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
out_lines.append('section divs: ' + str(len(section_divs)))

# Find all text content in the page
texts = re.findall(r'>([^<]+)<', html_content)
unique_texts = set()
for t in texts:
    t = t.strip()
    if len(t) > 3 and len(t) < 80 and 'http' not in t and 'BX' not in t and 'mailto' not in t:
        unique_texts.add(t)

out_lines.append('Unique short texts: ' + str(len(unique_texts)))
for t in sorted(unique_texts):
    out_lines.append('  ' + t)

out_path = r'C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_explore.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))

print('Done. Output:', out_path)
