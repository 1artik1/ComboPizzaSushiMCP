import re
with open(r'C:\Users\1artik1\AppData\Local\Temp\opencode\pizzeria_cuba_http.html', 'r', encoding='utf-8') as f:
    html = f.read()
print('Size:', len(html))

# Find API calls - look for fetch or XHR patterns
patterns = re.findall(r'(?:fetch|XMLHttpRequest|axios)\s*\([^)]*api[^)]*\)', html)
if patterns:
    print('API fetch patterns:', patterns[:5])
else:
    print('No fetch patterns found')

# Find all URLs
urls = re.findall(r'(https?://[^\s"\']+\b)', html)
unique_urls = sorted(set(urls))
print('Unique URLs:', len(unique_urls))
for u in unique_urls[:20]:
    print('  ' + u)

# Find the API endpoint used
api_refs = re.findall(r'vsem-edu-oblako\.ru/\S+', html)
if api_refs:
    print('API refs:', api_refs[:10])

# Find script tags with API config
scripts = re.findall(r'<script[^>]*>([^<]+)</script>', html)
for i, s in enumerate(scripts[:10]):
    if 'api' in s.lower() or 'vsem' in s.lower() or 'getHomeProducts' in s:
        print('API script ' + str(i) + ': ' + s[:300])

# Find all script tags with data
for i, s in enumerate(scripts):
    if len(s) > 500 and 'getHomeProducts' in s:
        print('Script ' + str(i) + ' has getHomeProducts')
        # Extract the URL
        m = re.search(r'(\S+api\S+)', s)
        if m:
            print('  URL: ' + m.group(1))
