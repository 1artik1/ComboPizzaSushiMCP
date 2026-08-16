# -*- coding: utf-8 -*-
"""ninja_food.py — парсер Ninja Food (ninjafood.su).

HTTP: HTML 477KB, 224 product cards (div.catalog_element).
- div.catalog_element: data-id, data-offers (price)
- span.old_price: старая цена
- span.new_price: новая цена (текущая)
- span.name / span.often_ordered_element_name: название товара
- Категория: из URL или контекста (Ланчи, Пицца, Роллы, Сеты, и т.д.)
- Вес: НЕТ на сайте → weight_g=None (это нормально)
- HTTP-only: парсим статический HTML, Playwright не нужен.
"""

import re
from bs4 import BeautifulSoup
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client


@chain("ninja_food")
class NinjaFoodParser(ChainParser):
    """Ninja Food — Bitrix-сайт. HTTP-only, DOM-атрибуты."""

    id = "ninja_food"
    name = "Ниндзя Фуд"
    city = "Воронеж"
    url = "https://ninjafood.su/"
    description = "Bitrix-сайт. Пицца, роллы, сеты, вок, ланчи."
    needs_playwright = False

    def parse(self):
        """Распарсить меню Ninja Food из HTML."""
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        html = http_client.fetch_html(url, chain_cfg)
        if html is None or len(html) < 10000:
            raise ChainUnavailable(
                "Ninja Food недоступен: HTTP не вернул HTML. "
                "Последняя попытка: " + url
            )

        return self._parse_html(html)

    def _parse_html(self, html):
        """Parse products from HTML using raw regex + BS4."""
        soup = BeautifulSoup(html, "html.parser")

        # --- Extract product cards ---
        # Each card: <div class="catalog_element box" data-id="40868">
        # Contains: name, old_price, new_price (price)
        products = []
        seen_names = set()

        for card in soup.find_all("div", class_=True):
            cls = str(card.get("class") or [])
            if "catalog_element" not in cls:
                continue

            pid = card.get("data-id") or ""
            if not pid:
                continue

            # Extract name from <span class="name"> or <span class="often_ordered_element_name">
            name = None
            for el in card.find_all(["a", "span"], class_=True):
                el_cls = str(el.get("class") or [])
                if "name" in el_cls and "often_ordered" not in el_cls:
                    t = el.get_text().strip()
                    if t and t not in seen_names:
                        name = t
                        seen_names.add(t)
                        break

            if not name:
                continue

            # Extract price from .new_price
            price = None
            for el in card.find_all("span", class_=True):
                el_cls = str(el.get("class") or [])
                if "new_price" in el_cls:
                    t = el.get_text() or ""
                    digits = re.findall(r"\d+", t)
                    if digits:
                        price = int(digits[0])
                    break

            # Skip items without price
            if price is None:
                continue

            products.append({
                "name": name,
                "weight_g": None,
                "price_rub": price,
                "is_from_price": False,
                "description": name,
                "category": "Каталог",
                "product_url": "",
            })

        return products
