# -*- coding: utf-8 -*-
"""sushi_darom.py — парсер Sushi Darom.

Перенесён из chains_other.py: 170 позиций, вес из parametr.outQuantity_raw.
"""

import re
import json
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client


@chain("sushi_darom")
class SushiDaromParser(ChainParser):
    """Парсер Sushi Darom — Next.js SPA, 170 items с REAL весами."""

    id = "sushi_darom"
    name = "Суши Даром"
    city = "Воронеж"
    url = "https://voronezh.sushi-darom.com/"
    description = "Сеть роллов и суши. Next.js-приложение."
    needs_playwright = False

    def parse(self):
        """Распарсить меню Sushi Darom."""
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        try:
            html = http_client.fetch_html(url, chain_cfg)
        except Exception as e:
            raise ChainUnavailable(f"Не удалось загрузить {url}: {e}")
        if html is None:
            raise ChainUnavailable(f"Не удалось загрузить {url}")

        products = []
        next_data = re.findall(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if next_data:
            try:
                data = json.loads(next_data[0])
                props = data.get('props', {})
                page_props = props.get('pageProps', {})

                # Build category mapping
                categories = page_props.get('categories', [])
                cat_map = {}
                if isinstance(categories, list):
                    for cat in categories:
                        if isinstance(cat, dict):
                            cat_id = str(cat.get('id', ''))
                            cat_name = cat.get('category', '')
                            if cat_id and cat_name:
                                cat_map[cat_id] = cat_name

                # Products
                offers = page_props.get('offers', [])
                if isinstance(offers, list):
                    for item in offers:
                        if not isinstance(item, dict):
                            continue
                        name = item.get('name', '')
                        price = item.get('price', 0)
                        if isinstance(price, str):
                            price = int(re.search(r'(\d+)', price).group(1))
                        elif isinstance(price, (int, float)):
                            price = int(price)

                        if name and price > 0:
                            # Extract weight from parametr.outQuantity_raw
                            weight = None
                            param = item.get('parametr', {})
                            if isinstance(param, dict):
                                out_raw = param.get('outQuantity_raw', '')
                                if out_raw:
                                    try:
                                        weight = int(out_raw)
                                    except (ValueError, TypeError):
                                        pass

                            category = cat_map.get(str(item.get('categoryId', '')), 'Роллы/Суши')
                            desc = item.get('structure', '') or item.get('description', '')
                            if not desc:
                                desc = name
                            products.append({
                                "name": name,
                                "weight_g": weight,
                                "price_rub": price,
                                "is_from_price": False,
                                "description": desc,
                                "category": category,
                                "product_url": url,
                            })
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        return products
