import os, re, json

# Explore ninja_food playwright HTML
path = r'C:\Users\1artik1\AppData\Local\Temp\opencode\ninja_playwright_kaliforniya.html'
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()
print('Size:', len(html_content))

# Find all text blocks
texts = re.findall(r'>([^<]+)<', html_content)
print('Text blocks:', len(texts))

# Print non-empty, non-script texts
for t in texts:
    t = t.strip()
    if len(t) > 5 and len(t) < 100 and 'BX' not in t and 'http' not in t:
        print(repr(t[:80]))
        break  # Just one

# Let's look at the HTML structure more carefully
# Find all tags
tag_pattern = r'<(\w+)[^>]*>'
tags = re.findall(tag_pattern, html_content)
from collections import Counter
tag_counts = Counter(tags)
print('Top tags:', tag_counts.most_common(20))

# Find divs with specific classes
div_pattern = r'<div[^>]*>'
divs = re.findall(div_pattern, html_content)
print('Total divs:', len(divs))

# Find all class attributes
class_pattern = r'class="([^"]*)"'
classes = re.findall(class_pattern, html_content)
class_counts = Counter(classes)
print('Top classes:', class_counts.most_common(30))
