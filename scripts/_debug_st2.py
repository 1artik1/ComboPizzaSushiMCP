# Quick sushi_time debug
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

chain_cfg = mcp_config.get_chain("sushi_time")
url = chain_cfg.get("url", "https://xn----8sbwgpzjf9b.xn--p1ai/Voronezh/")
html = http_client.fetch_html(url, chain_cfg)
print("HTML length:", len(html) if html else 0)

if html:
    soup = BeautifulSoup(html, "html.parser")
    
    # Count divs with tovar_small
    all_divs = soup.find_all("div", class_=True)
    print("All divs with class:", len(all_divs))
    
    tovar_small = [d for d in all_divs if "tovar_small" in (d.get("class") or [])]
    print("divs with tovar_small:", len(tovar_small))
    
    if tovar_small:
        first = tovar_small[0]
        print("First tovar_small:", first.name, first.get("class"), first.get("data-id"))
        
        # Find child a.linknoactive
        links = first.find_all("a", class_=True)
        print("Child a elements:", len(links))
        for a in links[:3]:
            a_cls = a.get("class") or []
            print(f"  a: class={a_cls} data-title={a.get('data-title')} data-cat={a.get('data-category-name')}")
        
        # Check text for weight
        text = first.get_text() or ""
        print("First 100 chars of text:", repr(text[:100]))
        m = re.search(r"(\d+)\s*[гг]", text)
        if m:
            print("Weight found:", m.group(1))
        
        # Check for sale-price spans
        spans = first.find_all("span", class_=True)
        print("Child span elements:", len(spans))
        for s in spans[:5]:
            s_cls = s.get("class") or []
            stext = s.get_text() or ""
            print(f"  span: class={s_cls} text={stext[:50]}")
