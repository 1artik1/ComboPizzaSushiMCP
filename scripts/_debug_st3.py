# Trace sushi_time parsing
import sys, os, codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

from combo_mcp import http_client
from combo_mcp import config as mcp_config
from bs4 import BeautifulSoup
import re

chain_cfg = mcp_config.get_chain("sushi_time")
html = http_client.fetch_html("https://xn----8sbwgpzjf9b.xn--p1ai/Voronezh/", chain_cfg)
soup = BeautifulSoup(html, "html.parser")

count = 0
products = []
cards = soup.find_all("div", class_=True)
for card in cards:
    cls = card.get("class") or []
    if "tovar_small" not in cls:
        continue

    pid = card.get("data-id") or ""
    if not pid:
        continue

    name = None
    category = "Роллы/Суши"
    for child in card.find_all("a", class_=True):
        child_cls = child.get("class") or []
        if "linknoactive" in child_cls:
            title = child.get("data-title") or ""
            if isinstance(title, str) and title.strip():
                name = title.strip()
            cat = child.get("data-category-name") or ""
            if isinstance(cat, str) and cat.strip():
                category = cat.strip()
            break

    if not name:
        continue

    weight = None
    text = card.get_text() or ""
    m = re.search(r"(\d+)\s*[гг]", text)
    if m:
        weight = int(m.group(1))

    price = None
    for span in card.find_all("span", class_=True):
        span_cls = span.get("class") or []
        for c in span_cls:
            if "sale-price" in str(c):
                stext = span.get_text() or ""
                print(f"  span class={span_cls} text='{stext[:60]}'")
                pm = re.search(r"(\d+)", stext)
                if pm:
                    price = int(pm.group(1))
                    print(f"    price={price}")
                break

    print(f"id={pid} name={name} weight={weight} price={price} cat={category}")
    if name and price:
        count += 1
        products.append({"name": name, "weight_g": weight, "price_rub": price})

print(f"\nTotal products: {count}")
