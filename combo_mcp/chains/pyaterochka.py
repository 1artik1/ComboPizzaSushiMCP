# -*- coding: utf-8 -*-
"""pyaterochka.py — парсер Пятёрочка (доставка).

Продуктовый магазин Пятёрочка: API через Playwright (анти-бот защита).
Паттерн: with pw as p: (в Playwright 1.62 as-переменная — Playwright объект).
"""

import re
import json
import urllib.parse
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp.playwright_client import get_playwright


@chain("pyaterochka")
class PyaterochkaParser(ChainParser):
    """Парсер Пятёрочка (доставка)."""

    id = "pyaterochka"
    name = "Пятёрочка (доставка)"
    city = "Россия"
    url = "https://5ka.ru/"
    description = "Продуктовый магазин Пятёрочка: API через браузер"
    needs_playwright = True
    category_map = {}
    has_server_search = True

    STORE_ID = "35XY"
    BASE_URL = "https://5d.5ka.ru"
    PAGE_LIMIT = 12
    MAX_PAGES_PER_CATEGORY = 20

    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    _WEIGHT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(кг|г|мл|л)\b", re.IGNORECASE)

    def _api_call(self, p, page, path, params=None):
        url = self.BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        result = page.evaluate(
            """
            async (url) => {
                const r = await fetch(url, {
                    headers: {'accept': 'application/json'}
                });
                return {status: r.status, body: await r.text()};
            }
            """,
            url,
        )
        if result.get("status") != 200:
            raise ChainUnavailable(
                f"pyaterochka: API вернул {result.get('status')}: "
                f"{result.get('body', '')[:200]}"
            )
        try:
            return json.loads(result.get("body", "{}"))
        except json.JSONDecodeError:
            raise ChainUnavailable(
                f"pyaterochka: невалидный JSON: {result.get('body', '')[:200]}"
            )

    def _parse_weight_from_name(self, name):
        m = self._WEIGHT_RE.search(name)
        if m:
            value = float(m.group(1).replace(",", "."))
            unit = m.group(2).lower()
            if unit in ("кг", "л"):
                return round(value * 1000)
            elif unit in ("г", "мл"):
                return round(value)
        return 0

    def _map_product(self, product, category_name):
        name = product.get("name", "")
        prices = product.get("prices", {}) or {}
        regular = prices.get("regular", "0")
        try:
            price_rub = round(float(regular))
        except (ValueError, TypeError):
            price_rub = 0

        old_price_rub = None
        discount = prices.get("discount")
        if discount:
            try:
                old_price_rub = round(float(discount))
            except (ValueError, TypeError):
                pass

        weight_g = 0
        weight_source = "none"
        property_clar = product.get("property_clarification")
        if property_clar:
            weight_g = self._parse_weight_from_name(property_clar)
            if weight_g > 0:
                weight_source = "site"
            else:
                weight_g = self._parse_weight_from_name(name)
                if weight_g > 0:
                    weight_source = "name"

        in_stock = product.get("is_available", False)

        return {
            "name": name,
            "price_rub": price_rub,
            "old_price_rub": old_price_rub,
            "weight_g": weight_g,
            "weight_source": weight_source,
            "category": category_name,
            "in_stock": in_stock,
            "item_id": str(product.get("plu", "")),
            "description": "",
        }

    def _fetch_category_products(self, p, page, cat_id, cat_name):
        items = []
        offset = 0
        for _page_num in range(self.MAX_PAGES_PER_CATEGORY):
            path = (
                f"/api/catalog/v2/stores/{self.STORE_ID}/categories/{cat_id}/products"
            )
            params = {
                "mode": "delivery",
                "include_restrict": "true",
                "limit": self.PAGE_LIMIT,
                "offset": offset,
            }
            try:
                resp = self._api_call(p, page, path, params)
            except ChainUnavailable:
                break
            products = resp.get("products") or []
            if not products:
                break
            for raw_product in products:
                mapped = self._map_product(raw_product, cat_name)
                if mapped["price_rub"] > 0:
                    items.append(mapped)
            if len(products) < self.PAGE_LIMIT:
                break
            offset += self.PAGE_LIMIT
        return items

    def _open_page(self, p):
        """Открыть страницу, проверить капчу. Возвращает (page, browser)."""
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=self.UA,
            locale="ru-RU",
        )
        page = context.new_page()
        page.goto(
            "https://5ka.ru/catalog/", timeout=30000, wait_until="domcontentloaded"
        )
        page.wait_for_timeout(5000)

        current_url = page.url.lower()
        content = page.content().lower()
        is_challenge = (
            "/xpvnsulc/" in current_url
            or "rotated_captcha" in content
            or "sp_rotated_captcha" in content
            or "проверк" in content
        )
        if is_challenge:
            browser.close()
            raise ChainUnavailable(
                "pyaterochka: анти-бот капча Пятёрочки — попробуйте позже"
            )
        return page, browser

    def parse(self):
        pw = get_playwright()
        if pw is None:
            raise ChainUnavailable("pyaterochka: Playwright не установлен")
        with pw as p:
            browser = None
            try:
                page, browser = self._open_page(p)
            except ChainUnavailable:
                raise
            try:
                path = (
                    f"/api/catalog/v3/stores/{self.STORE_ID}/categories"
                    f"?mode=delivery&include_subcategories=1&include_restrict=true"
                )
                try:
                    resp = self._api_call(p, page, path)
                except ChainUnavailable:
                    raise
                groups = resp if isinstance(resp, list) else []
                if not groups:
                    raise ChainUnavailable("pyaterochka: категории пусты")

                all_items = []
                seen_plu = set()
                for group in groups:
                    for subcat in group.get("categories", []):
                        subcat_id = subcat.get("id", "")
                        subcat_name = subcat.get("name", "")
                        if not subcat_id:
                            continue
                        items = self._fetch_category_products(
                            p, page, subcat_id, subcat_name
                        )
                        for item in items:
                            iid = item.get("item_id", "")
                            if iid and iid not in seen_plu:
                                seen_plu.add(iid)
                                all_items.append(item)
                return all_items
            except ChainUnavailable:
                raise
            except Exception as e:
                raise ChainUnavailable(f"pyaterochka: ошибка: {e}")
            finally:
                if browser is not None:
                    browser.close()

    def search(self, query, limit=20):
        pw = get_playwright()
        if pw is None:
            return []
        with pw as p:
            browser = None
            try:
                page, browser = self._open_page(p)
            except ChainUnavailable:
                return []
            try:
                path = f"/api/catalog/v3/stores/{self.STORE_ID}/search"
                params = {
                    "mode": "delivery",
                    "include_restrict": "true",
                    "q": query,
                    "limit": min(limit, self.PAGE_LIMIT),
                }
                try:
                    resp = self._api_call(p, page, path, params)
                except ChainUnavailable:
                    return []
                products = resp.get("products") or []
                items = []
                seen_plu = set()
                for raw_product in products:
                    plu = raw_product.get("plu", 0)
                    if plu in seen_plu:
                        continue
                    seen_plu.add(plu)
                    mapped = self._map_product(raw_product, "")
                    if mapped["price_rub"] > 0:
                        items.append(mapped)
                    if len(items) >= limit:
                        break
                return items
            except ChainUnavailable:
                return []
            except Exception:
                return []
            finally:
                if browser is not None:
                    browser.close()

    def get_categories(self):
        pw = get_playwright()
        if pw is None:
            return []
        with pw as p:
            browser = None
            try:
                page, browser = self._open_page(p)
            except ChainUnavailable:
                return []
            try:
                path = (
                    f"/api/catalog/v3/stores/{self.STORE_ID}/categories"
                    f"?mode=delivery&include_subcategories=1&include_restrict=true"
                )
                try:
                    resp = self._api_call(p, page, path)
                except ChainUnavailable:
                    return []
                groups = resp if isinstance(resp, list) else []
                result = []
                for group in groups:
                    entry = {
                        "id": group.get("id", ""),
                        "name": group.get("name", ""),
                        "children": [],
                    }
                    for subcat in group.get("categories", []):
                        entry["children"].append(
                            {
                                "id": subcat.get("id", ""),
                                "name": subcat.get("name", ""),
                            }
                        )
                    result.append(entry)
                return result
            except ChainUnavailable:
                return []
            except Exception:
                return []
            finally:
                if browser is not None:
                    browser.close()
