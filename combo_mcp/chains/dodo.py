# -*- coding: utf-8 -*-
"""dodo.py — парсер Dodo Pizza (dodopizza.ru).

HTTP API: /api/v5/menu/delivery/countries/643/localities/...
- variations[].product.price: цена
- variations[].product.foodValue.weight: вес в граммах
- description: состав
- Берём первый вариант (базовый размер) для каждой позиции
"""

import re
import json
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client
from combo_mcp import playwright_client


@chain("dodo")
class DodoParser(ChainParser):
    """Dodo Pizza — API с fallback на Playwright."""

    id = "dodo"
    name = "Додо Пицца"
    city = "Воронеж"
    url = "https://dodopizza.ru"
    description = "Крупная сеть. API с fallback на Playwright."
    needs_playwright = False

    API_URL = (
        "https://dodopizza.ru/api/v5/menu/delivery/"
        "countries/643/localities/"
        "00000193-0000-0000-0000-000000000000"
    )

    def parse(self):
        """Распарсить меню Dodo Pizza."""
        chain_cfg = mcp_config.get_chain(self.id)
        api_url = self.API_URL

        # Try HTTP first with browser headers
        data = self._fetch_http(api_url, chain_cfg)

        # Fallback: Playwright
        if data is None:
            data = self._fetch_playwright(api_url, chain_cfg)

        if data is None:
            raise ChainUnavailable(
                "Dodo Pizza API недоступен: HTTP 403/капча + Playwright не помог. "
                "Возможно, сайт требует JavaScript-сессии."
            )

        products = self._parse_api(data)

        if not products:
            raise ChainUnavailable(
                "Dodo Pizza: API вернул пустой результат. "
                "Структура API могла измениться."
            )

        return products

    def _fetch_http(self, url, chain_cfg):
        """Try HTTP request with browser headers."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://dodopizza.ru/",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            session, timeout = http_client.get_session(chain_cfg)
            session.headers.update(headers)
            r = session.get(url, timeout=timeout, verify=False, allow_redirects=True)

            if r.status_code == 200:
                return r.json()
            elif r.status_code == 403:
                return None
            else:
                return None
        except Exception:
            return None

    def _fetch_playwright(self, url, chain_cfg):
        """Fallback: Playwright to intercept the API response."""
        try:
            page, browser = playwright_client.get_page("https://dodopizza.ru/")

            # Intercept the API response
            captured = []

            def on_response(response):
                if url in response.url:
                    try:
                        captured.append(response.json())
                    except Exception:
                        pass

            page.on("response", on_response)

            # Navigate to the API URL
            try:
                resp = page.goto(url, timeout=30000)
                if resp and resp.status == 200:
                    try:
                        data = resp.json()
                        browser.close()
                        return data
                    except Exception:
                        pass
            except Exception:
                pass

            # Try to find the captured response
            if captured:
                browser.close()
                return captured[0]

            browser.close()
            return None
        except Exception:
            return None

    def _parse_api(self, data):
        """Parse products from Dodo API response."""
        products = []
        items = data.get("items", [])

        if not isinstance(items, list):
            return []

        for item in items:
            if not isinstance(item, dict):
                continue

            name = item.get("name", "").strip()
            if not name:
                continue

            # Get first variation (smallest size = base price)
            variations = item.get("variations", [])
            if not isinstance(variations, list) or not variations:
                continue

            first_var = variations[0]
            if not isinstance(first_var, dict):
                continue

            product = first_var.get("product", {})
            if not isinstance(product, dict):
                continue

            price = product.get("price")
            if price is None:
                continue
            try:
                price = int(price)
            except (ValueError, TypeError):
                continue

            if price <= 0:
                continue

            # Get weight from foodValue
            weight = None
            food_value = product.get("foodValue", {})
            if isinstance(food_value, dict):
                w = food_value.get("weight")
                if w is not None:
                    try:
                        weight = int(w)
                    except (ValueError, TypeError):
                        pass

            # Get description
            description = item.get("description", "").strip()
            if not description:
                description = name

            products.append({
                "name": name,
                "weight_g": weight,
                "price_rub": price,
                "is_from_price": False,
                "description": description,
                "category": "Пицца",
                "product_url": self.url,
            })

        return products
