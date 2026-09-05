# -*- coding: utf-8 -*-
"""magnit.py — парсер Магнит (доставка).

Продуктовый магазин Магнит: API через requests, категории + поиск товаров.
"""

import re
import json
import time
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client


@chain("magnit")
class MagnitParser(ChainParser):
    """Парсер Магнит (доставка)."""

    id = "magnit"
    name = "Магнит (доставка)"
    city = "Россия"
    url = "https://magnit.ru/"
    description = "Продуктовый магазин Магнит: поиск товаров и категории"
    needs_playwright = False
    category_map = {}  # не нужен — категории серверные
    has_server_search = True

    # Константы API
    STORE_CODE = "992301"
    CATALOG_TYPE = "3"
    STORE_TYPE = "dostavka"
    MAX_PAGES_PER_CATEGORY = 4
    PAGE_LIMIT = 32  # API принимает до 32 за запрос
    REQUEST_PAUSE = 0.3

    # Заголовки для API
    HEADERS = {
        "accept": "application/json",
        "content-type": "application/json",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "x-client-name": "magnit",
        "x-new-magnit": "true",
        "x-device-platform": "Web",
        "x-platform-version": "Windows Chrome 126",
        "x-device-id": "71389c5f-f647-432e-be83-032c3a20698c",
        "x-app-version": "2026.8.21-15.54",
        "referer": "https://magnit.ru/",
    }

    # Регэксп для веса из имени товара
    _WEIGHT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(кг|г|мл|л|шт)\b", re.IGNORECASE)

    def _session(self):
        """Создать requests.Session с заголовками Магнита."""
        session = http_client.requests.Session()
        session.headers.update(self.HEADERS)
        return session

    def _api_get(self, url, params=None, timeout=15):
        """GET запрос к API Магнита."""
        s = self._session()
        try:
            r = s.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            raise ChainUnavailable(
                f"magnit: API вернул {r.status_code}: {r.text[:200]}"
            )
        except ChainUnavailable:
            raise
        except Exception as e:
            raise ChainUnavailable(f"magnit: GET ошибка: {e}")

    def _api_post(self, url, body, timeout=15):
        """POST запрос к API Магнита."""
        s = self._session()
        try:
            r = s.post(
                url,
                headers=self.HEADERS,
                data=json.dumps(body, ensure_ascii=False),
                timeout=timeout,
            )
            if r.status_code == 200:
                return r.json()
            raise ChainUnavailable(
                f"magnit: API вернул {r.status_code}: {r.text[:200]}"
            )
        except ChainUnavailable:
            raise
        except Exception as e:
            raise ChainUnavailable(f"magnit: POST ошибка: {e}")

    def _parse_weight_from_name(self, name):
        """Извлечь вес из имени товара.

        Возвращает weight_g (int) или 0.
        кг/л -> *1000, г/мл -> как есть, округляем.
        """
        m = self._WEIGHT_RE.search(name)
        if m:
            value = float(m.group(1).replace(",", "."))
            unit = m.group(2).lower()
            if unit in ("кг", "л"):
                return round(value * 1000)
            elif unit in ("г", "мл"):
                return round(value)
            elif unit == "шт":
                return 0
        return 0

    def _map_item(self, item, top_category_name):
        """Маппинг сырого item API в стандартную позицию."""
        name = item.get("name", "")
        price_cents = item.get("price")
        if price_cents is None:
            price_cents = 0
        price_rub = round(price_cents / 100)

        # Старая цена (промо)
        old_price_rub = None
        promo = item.get("promotion")
        if promo and isinstance(promo, dict) and promo.get("isPromotion"):
            old_price_cents = promo.get("oldPrice")
            if old_price_cents is None:
                old_price_cents = 0
            old_price_rub = round(old_price_cents / 100)

        # Вес
        weight_g = 0
        weight_source = "none"
        weighted = item.get("weighted")
        if weighted and isinstance(weighted, dict) and weighted.get("isWeighted"):
            weight_g = weighted.get("shelfWeight", 0)
            weight_source = "site"
        else:
            weight_g = self._parse_weight_from_name(name)
            if weight_g > 0:
                weight_source = "name"

        # Наличие
        quantity = item.get("quantity")
        in_stock = True if quantity is None or quantity > 0 else False

        return {
            "name": name,
            "price_rub": price_rub,
            "old_price_rub": old_price_rub,
            "weight_g": weight_g,
            "weight_source": weight_source,
            "category": top_category_name,
            "in_stock": in_stock,
            "item_id": str(item.get("id", "")),
            "description": "",
        }

    def _fetch_category_items(self, cat_id, cat_name, session):
        """Загрузить товары одной категории с пагинацией."""
        items = []
        seen_ids = set()
        offset = 0

        for page in range(self.MAX_PAGES_PER_CATEGORY):
            body = {
                "categories": [cat_id],
                "includeAdultGoods": True,
                "pagination": {"limit": self.PAGE_LIMIT, "offset": offset},
                "sort": {"order": "desc", "type": "popularity"},
                "storeCode": self.STORE_CODE,
                "storeType": self.STORE_TYPE,
                "catalogType": self.CATALOG_TYPE,
            }
            try:
                resp = self._api_post("https://magnit.ru/webgate/v2/goods/search", body)
            except ChainUnavailable:
                break

            goods_items = resp.get("items") or []
            if not goods_items:
                break

            pagination = resp.get("pagination", {})
            has_more = pagination.get("hasMore", False)
            next_offset = pagination.get("nextOffset")

            for raw_item in goods_items:
                item_id = str(raw_item.get("id", ""))
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                mapped = self._map_item(raw_item, cat_name)
                if mapped["price_rub"] > 0:
                    items.append(mapped)

            if not has_more or not next_offset:
                break
            offset = next_offset

            time.sleep(self.REQUEST_PAUSE)

        return items

    def _fetch_categories(self):
        """GET категорий из API."""
        return self._api_get(
            "https://magnit.ru/webgate/v3/categories/store/" + self.STORE_CODE,
            params={"storetype": self.STORE_TYPE, "catalogtype": self.CATALOG_TYPE},
        )

    def parse(self):
        """Распарсить меню Магнит: все топ-категории + товары."""
        try:
            cat_data = self._fetch_categories()
        except ChainUnavailable:
            raise
        except Exception as e:
            raise ChainUnavailable(f"magnit: не удалось загрузить категории: {e}")

        top_categories = cat_data.get("items", [])
        if not top_categories:
            raise ChainUnavailable("magnit: категории пусты")

        all_items = []
        seen_ids = set()

        for cat in top_categories:
            cat_id = cat.get("id")
            cat_name = cat.get("name", "")
            if not cat_id or not cat_name:
                continue

            items = self._fetch_category_items(cat_id, cat_name, None)
            for item in items:
                item_id = item.get("item_id", "")
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    all_items.append(item)

            time.sleep(self.REQUEST_PAUSE)

        return all_items

    def search(self, query, limit=20):
        """Поиск товаров по тексту."""
        all_items = []
        seen_ids = set()
        offset = 0

        while len(all_items) < limit:
            body = {
                "term": query,
                "includeAdultGoods": True,
                "pagination": {"limit": min(limit, self.PAGE_LIMIT), "offset": offset},
                "sort": {"order": "desc", "type": "popularity"},
                "storeCode": self.STORE_CODE,
                "storeType": self.STORE_TYPE,
                "catalogType": self.CATALOG_TYPE,
            }
            try:
                resp = self._api_post("https://magnit.ru/webgate/v2/goods/search", body)
            except ChainUnavailable:
                break

            goods_items = resp.get("items") or []
            if not goods_items:
                break

            pagination = resp.get("pagination", {})
            has_more = pagination.get("hasMore", False)

            for raw_item in goods_items:
                item_id = str(raw_item.get("id", ""))
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                mapped = self._map_item(raw_item, "")
                if mapped["price_rub"] > 0:
                    all_items.append(mapped)
                if len(all_items) >= limit:
                    break

            if not has_more:
                break
            offset = pagination.get("nextOffset", offset + self.PAGE_LIMIT)
            time.sleep(self.REQUEST_PAUSE)

        return all_items[:limit]

    def get_categories(self):
        """Дерево категорий сервера."""
        cat_data = self._fetch_categories()
        top_categories = cat_data.get("items", [])

        def _build_tree(cat):
            result = {
                "id": cat.get("id"),
                "name": cat.get("name", ""),
                "seo_code": cat.get("seoCode", ""),
                "children_count": len(cat.get("children", [])),
                "children": [],
            }
            for child in cat.get("children", []):
                result["children"].append(_build_tree(child))
            return result

        return [_build_tree(cat) for cat in top_categories]
