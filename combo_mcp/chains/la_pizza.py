# -*- coding: utf-8 -*-
"""la_pizza.py — парсер La Pizza, обёрнут в класс.

Перенесён из chains_la_pizza.py.
"""

import re
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client
from combo_mcp.chains.extra_utils import fetch_text, source


@chain("la_pizza")
class LaPizzaParser(ChainParser):
    """Парсер La Pizza."""

    id = "la_pizza"
    name = "Ла Пицца"
    city = "Воронеж"
    url = "https://la-pizza.pro"
    description = "Сеть доставки пиццы. Каталог: обычные, гигант, римские + комбо."
    needs_playwright = False

    DELIVERY_URL = "https://la-pizza.pro/info/9707"
    ACTIONS_URL = "https://la-pizza.pro/actions"

    def parse_extra(self):
        """Доставка и акции La Pizza (страницы «Доставка и оплата», «Акции»)."""
        cfg = mcp_config.get_chain(self.id)

        delivery = None
        dtext = fetch_text(self.DELIVERY_URL, cfg)
        if dtext:
            min_order = None
            m = re.search(r"Минимальная сумма заказа составляет (\d+) рублей", dtext)
            if m:
                min_order = int(m.group(1))
            delivery = {
                "min_order_rub": min_order,
                "cost_rub": None,
                "free_from_rub": None,
                "time_minutes": "09:00–23:00",
                "conditions": (
                    "Стоимость доставки уточняется у оператора. Курьер ожидает 10 минут; "
                    "повторная доставка от 180 ₽; заказы от 5000 ₽ — полная предоплата; "
                    "первый заказ от 3000 ₽ — предоплата; самовывоз до 23:30; "
                    "скидки не суммируются с акциями."
                ),
                "source": source(self.DELIVERY_URL),
            }

        promotions = []
        atext = fetch_text(self.ACTIONS_URL, cfg)
        if atext:
            m = re.search(r"При самовывозе скидка 100 рублей", atext)
            if m:
                promotions.append({
                    "title": "Скидка 100 ₽ при самовывозе",
                    "conditions": (
                        "Распространяется только на пиццу. Акции не суммируются."
                    ),
                    "valid_until": None,
                    "source": source(self.ACTIONS_URL),
                })

        return {"delivery": delivery, "loyalty": None, "promotions": promotions}

    CATALOGS = [
        "/catalog/picci-41-sm-33-sm-i-21-sm",
        "/catalog/bolshie-picci-50-i-45-sm",
        "/catalog/rimskie-picci",
    ]

    COMBO_IDS = {
        "102895237": 3000,
        "102893220": 2000,
    }

    def _fetch(self, url, timeout=10):
        """Fetch URL using http_client."""
        try:
            r = http_client.requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return None

    def _extract_weight(self, html):
        m = re.search(r'<span[^>]*>\s*(\d+)\s*[г\u0413\u20ac]\s*</span>', html)
        if m:
            return int(m.group(1))
        m = re.search(r'<div[^>]*text-gray[^>]*>\s*(\d+)\s*[г\u0413\u20ac]\s*</div>', html)
        if m:
            return int(m.group(1))
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if h1:
            h1_idx = h1.start()
            window = html[max(0, h1_idx):min(len(html), h1_idx + 800)]
            m = re.search(r'(\d+)\s*[г\u0413\u20ac]', window)
            if m:
                return int(m.group(1))
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for s in scripts:
            if len(s) > 5000:
                m = re.search(r',"(\u041d\u0430\u0442\u0443\u0440\u0430\u043b\u044c\u043d\u044b\u0435[^"]+)",\s*(?:\d+),\s*null,\s*"(\d+)"', s)
                if not m:
                    m = re.search(r',"(\u041d\u0430\u0442\u0443\u0440\u0430\u0442\u044c\u043d\u044b\u0439[^"]+)",\s*(?:\d+),\s*null,\s*"(\d+)"', s)
                if m:
                    return int(m.group(2))
        return 0

    def _extract_price(self, html):
        add_idx = html.find("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c")
        if add_idx > 0:
            window = html[add_idx:add_idx + 500]
            m = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', window)
            if m:
                return int(m.group(1).replace(' ', '').replace('\u00a0', ''))
        m = re.search(r'<div[^>]*text-lg[^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            div_text = m.group(1)
            div_text = re.sub(r'\s*\u043e\u0442\s*', '', div_text)
            m2 = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', div_text)
            if m2:
                return int(m2.group(1).replace(' ', '').replace('\u00a0', ''))
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if h1:
            h1_idx = h1.start()
            window = html[max(0, h1_idx):min(len(html), h1_idx + 1500)]
            m = re.search(r'(\d+(?:\s\d+)*)\s*[₽\u20bd]', window)
            if m:
                return int(m.group(1).replace(' ', '').replace('\u00a0', ''))
        return 0

    def _extract_name(self, html):
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if m:
            return re.sub(r'\s+', ' ', m.group(1)).strip()
        return ""

    def _extract_description(self, html):
        m = re.search(r'class="prose[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            desc = m.group(1).strip()
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.replace('\u003Cbr\u002F>', '').replace('\u003Cbr>', '').replace('\n', ' ').strip()
            if len(desc) > 10:
                return desc
        for m in re.finditer('"Натуральный', html):
            start = m.start()
            quote_start = start + 1
            quote_end = quote_start
            while quote_end < len(html):
                if html[quote_end] == '"' and (quote_end == quote_start or html[quote_end - 1] != '\\'):
                    break
                quote_end += 1
            if quote_end < len(html):
                desc = html[quote_start + 1:quote_end]
                after = html[quote_end:].strip()
                if re.match(r',\s*\d+,\s*null,\s*\d+', after):
                    desc = desc.replace('\u003Cbr\u002F>', '').replace('\u003Cbr>', '').replace('\n', ' ').strip()
                    if len(desc) > 10:
                        return desc
        m = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
        if m:
            return m.group(1)
        return ""

    def _parse_product_page(self, product_url):
        html = self._fetch(product_url)
        if html is None:
            return None
        name = self._extract_name(html)
        weight = self._extract_weight(html)
        price = self._extract_price(html)
        description = self._extract_description(html)
        if not name:
            return None
        return {
            "name": name,
            "weight_g": weight,
            "price_rub": price,
            "description": description,
            "category": "обычная",
            "product_url": product_url,
        }

    def _parse_catalog(self, catalog_url):
        html = self._fetch(catalog_url)
        if html is None:
            return []
        links = re.findall(r'href="(/product/\d+)"', html)
        return list(set(links))

    def parse(self):
        """Распарсить меню La Pizza."""
        from combo_mcp import config as mcp_config
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)
        timeout = chain_cfg.get("ttl_minutes", 10)
        if isinstance(timeout, (int, float)) and timeout <= 60:
            timeout = float(timeout)
        else:
            timeout = 10

        products = []
        cat_links = {}
        for cat_url in self.CATALOGS:
            full_url = url + cat_url
            links = self._parse_catalog(full_url)
            for link in links:
                cat_links[link] = cat_url
        for pid in self.COMBO_IDS:
            cat_links[f"/product/{pid}"] = "/catalog/combo"

        for link in sorted(cat_links.keys()):
            product_url = url + link
            cat = cat_links[link]
            if "picci-41" in cat:
                category = "обычная"
            elif "bolshie" in cat:
                category = "гигант"
            elif "rimskie" in cat:
                category = "римская"
            elif "combo" in cat:
                category = "комбо"
            else:
                category = "обычная"
            prod = self._parse_product_page(product_url)
            if prod is None:
                continue
            prod["category"] = category
            if category == "комбо" and prod["weight_g"] == 0:
                pid = link.replace("/product/", "")
                prod["weight_g"] = self.COMBO_IDS.get(pid, 0)
            products.append(prod)

        return products
