# -*- coding: utf-8 -*-
"""sushi_darom.py — парсер Sushi Darom.

Перенесён из chains_other.py: 170 позиций, вес из parametr.outQuantity_raw.
"""

import re
import json
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client
from combo_mcp.chains.extra_utils import clean_promo_desc, source


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

    # ------------------------------------------------------------------
    # Доп. информация: доставка, акции (Next.js data API)
    # ------------------------------------------------------------------

    def parse_extra(self):
        """Доставка (время/ожидание) и акции из _next/data index.json.

        Акции: promotions[] (title/description) + banners[] (сроки) в pageProps
        главной страницы; buildId берём из HTML.
        """
        cfg = mcp_config.get_chain(self.id)
        url = cfg.get("url", self.url)
        base = url.rstrip("/")

        # --- доставка: время работы и ожидание из JSON на странице /delivery ---
        delivery = None
        try:
            dhtml = http_client.fetch_html(f"{base}/delivery", cfg)
            if dhtml:
                wt = re.search(r'"work_time":\[\{"start":"(\d+:\d+):00","end":"(\d+:\d+):00"',
                               dhtml)
                td = re.search(r'"time_default_delivery":"(\d+)"', dhtml)
                pd_name = re.search(r'"name":"(Платная доставка[^"]*)"', dhtml)
                pd_min = re.search(r'"min_price":"(\d+)"', dhtml)
                pd_max = re.search(r'"max_price":"(\d+)"', dhtml)
                if wt or td or pd_name:
                    hours = f"{wt.group(1)}–{wt.group(2)}" if wt else "см. сайт"
                    min_order = int(pd_min.group(1)) if pd_min else None
                    cost = 99 if pd_name else None
                    delivery = {
                        "min_order_rub": min_order,
                        "cost_rub": cost,
                        "free_from_rub": None,
                        "time_minutes": hours,
                        "conditions": (
                            "Среднее время доставки "
                            + (f"~{td.group(1)} мин" if td else "см. сайт")
                            + (f"; «{pd_name.group(1)}»: заказы "
                               f"{pd_min.group(1)}–{pd_max.group(1)} ₽" if pd_name
                               else "; условия по адресу — на Яндекс-карте "
                                   "на странице «Доставка и самовывоз»")
                            + "."
                        ),
                        "source": source(f"{base}/delivery"),
                    }
        except Exception:
            delivery = None

        # --- акции: Next.js data API ---
        promotions = []
        try:
            main_html = http_client.fetch_html(base + "/", cfg)
            build = None
            if main_html:
                m = re.search(r'"buildId"\s*:\s*"([^"]+)"', main_html)
                if m:
                    build = m.group(1)
            if build:
                api = (f"{base}/_next/data/{build}/index.json"
                       f"?tenant=sushidarom&subdomain=voronezh")
                data = http_client.fetch_html(api, cfg)
                if data:
                    j = json.loads(data)
                    pp = j.get("pageProps") or {}
                    banners = pp.get("banners", {}) or {}
                    promos = pp.get("promotions", {}) or {}
                    for bid, b in banners.items():
                        if not isinstance(b, dict):
                            continue
                        title = b.get("title") or ""
                        if not title:
                            continue
                        p = promos.get(str(b.get("promo_id", "")), {})
                        desc = clean_promo_desc(p.get("description") or "")
                        if not desc:
                            desc = title
                        promotions.append({
                            "title": title,
                            "conditions": desc[:400],
                            "valid_until": b.get("date_visible_end"),
                            "source": source(base + "/"),
                        })
        except Exception:
            pass

        return {"delivery": delivery, "loyalty": None, "promotions": promotions}
