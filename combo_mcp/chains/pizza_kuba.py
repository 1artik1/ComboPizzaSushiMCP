# -*- coding: utf-8 -*-
"""pizza_kuba.py — парсер Pizza Kubа (pizzeriacuba.ru).

HTTP: API https://vsem-edu-oblako.ru/singlemerchant/api/getHomeProducts
с GET-параметрами (device_id, merchant_keys, и т.д.)
- category.name: категория
- item_name: название
- price: JSON {"size_id": "price"} → берём минимальную цену
- item_massa: обычно пустой → вес из названия размера: "33см (1кг)", "41см (1.5кг)", "150 г", "1 литр"
- item_description: состав (если есть)
"""

import re
import json
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client
from combo_mcp.chains.extra_utils import fetch_text, source


@chain("pizza_kuba")
class PizzaKubaParser(ChainParser):
    """Pizza Kubа — API на платформе vsem-edu-oblako."""

    id = "pizza_kuba"
    name = "Пицца Куба"
    city = "Воронеж"
    url = "https://pizzeriacuba.ru/"
    description = "Пиццерия с доставкой. API vsem-edu-oblako."
    needs_playwright = False

    DELIVERY_URL = "https://pizzeriacuba.ru/info/4220"
    ACTIONS_URL = "https://pizzeriacuba.ru/actions"

    def parse_extra(self):
        """Доставка и акции Пицца Куба."""
        cfg = mcp_config.get_chain(self.id)

        delivery = None
        dtext = fetch_text(self.DELIVERY_URL, cfg)
        if dtext:
            delivery = {
                "min_order_rub": None,
                "cost_rub": 0,
                "free_from_rub": 0,
                "time_minutes": "10:00–00:00 / 00:01–09:00 (круглосуточно)",
                "conditions": (
                    "Днём доставка бесплатная (в зоне), от одной пиццы; ночью (23:50–09:00) "
                    "150–200 ₽ по зоне; вне зоны +30 ₽/км; красная зона — мин. заказ 2500 ₽ "
                    "или +100 ₽; серая зона — 3500 ₽ или +200 ₽; повторная доставка 150 ₽; "
                    "курьер ожидает 15 минут."
                ),
                "source": source(self.DELIVERY_URL),
            }

        promotions = []
        atext = fetch_text(self.ACTIONS_URL, cfg)
        if atext:
            known = [
                ("Еженедельный розыгрыш пицц", "Еженедельный розыгрыш пицц.", None),
                ("Скидка 100 ₽ при самовывозе", "Скидка 100 рублей при самовывозе с каждой пиццы.", None),
                ("Скидка 7% на доставку от 5000 ₽", "Дарим скидочку 7% на доставку при заказе от 5000 рублей.", None),
                ("Доставка бесплатно", "Доставка бесплатно.", None),
            ]
            for title, cond, until in known:
                if title.split(" ")[0] in atext or cond[:30] in atext:
                    promotions.append({
                        "title": title, "conditions": cond,
                        "valid_until": until, "source": source(self.ACTIONS_URL),
                    })

        return {"delivery": delivery, "loyalty": None, "promotions": promotions}

    API_URL = "https://vsem-edu-oblako.ru/singlemerchant/api/getHomeProducts"

    API_PARAMS = {
        "device_id": "b14ed9d1-1adf-4778-90cf-32e234d7d66b",
        "device_platform": "desktop",
        "merchant_keys": "6be77015e90108fda45c894f345a5769",
        "transaction_type": "delivery",
        "json": "true",
        "lang": "ru",
        "frontend": "modern",
        "full": "true",
    }

    def parse(self):
        """Распарсить меню Pizza Kubа через API."""
        chain_cfg = mcp_config.get_chain(self.id)
        api_url = self.API_URL

        try:
            session, timeout = http_client.get_session(chain_cfg)
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://pizzeriacuba.ru/",
            })
            r = session.get(
                api_url,
                params=self.API_PARAMS,
                timeout=timeout,
                verify=False,
                allow_redirects=True,
            )

            if r.status_code != 200:
                raise ChainUnavailable(
                    f"Pizza Kubа API вернул {r.status_code}. "
                    "Требуется авторизация или другой эндпоинт."
                )

            text = r.text.strip()
            # Handle JSONP wrapper: ({...})
            if text.startswith("(") and text.endswith(")"):
                text = text[1:-1]

            data = json.loads(text)
        except ChainUnavailable:
            raise
        except Exception as e:
            raise ChainUnavailable(
                f"Pizza Kubа API недоступен: {e}. "
                "Эндпоинт: " + api_url
            )

        products = self._parse_api(data)

        if not products:
            raise ChainUnavailable(
                "Pizza Kubа: API вернул пустой результат. "
                "Структура API могла измениться."
            )

        return products

    def _parse_api(self, data):
        """Parse products from API response."""
        products = []
        details = data.get("details", {})
        categories = details.get("data", [])

        if not isinstance(categories, list):
            return []

        for cat in categories:
            if not isinstance(cat, dict):
                continue
            cat_name = cat.get("name", "Каталог")
            items = cat.get("items", [])
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                name = item.get("item_name", "").strip()
                if not name:
                    continue

                # Parse price: JSON string like {"size_id": "price"}
                price_raw = item.get("price", "")
                price = None
                if isinstance(price_raw, str):
                    try:
                        price_dict = json.loads(price_raw)
                        if isinstance(price_dict, dict):
                            # Find minimum price
                            min_price = None
                            for v in price_dict.values():
                                try:
                                    p = int(float(str(v)))
                                    if min_price is None or p < min_price:
                                        min_price = p
                                except (ValueError, TypeError):
                                    pass
                            price = min_price
                    except (json.JSONDecodeError, ValueError, TypeError):
                        pass

                if price is None or price <= 0:
                    continue

                # Parse weight: item_massa → размер минимальной цены → любой размер
                weight = None
                weight_source = "none"
                massa = item.get("item_massa", "")
                if isinstance(massa, str) and massa.strip():
                    m = re.search(r"(\d+)", massa)
                    if m:
                        weight = int(m.group(1))
                        weight_source = "site"
                if weight is None:
                    weight = self._weight_from_sizes(item.get("prices"), price)
                    if weight:
                        weight_source = "size_name"

                # Parse description
                description = item.get("item_description", "").strip()
                if not description:
                    description = name

                products.append({
                    "name": name,
                    "weight_g": weight,
                    "weight_source": weight_source,
                    "price_rub": price,
                    "is_from_price": True,
                    "description": description,
                    "category": cat_name,
                    "product_url": self.url,
                })

        return products

    def _weight_from_sizes(self, prices, min_price):
        """Вес из названия размера: '33см (1кг)', '41см (1.5кг)', '150 г', '1 литр'.

        Сначала размер, соответствующий минимальной цене, затем любой с весом.
        """
        if not isinstance(prices, list):
            return None

        for p in prices:
            if not isinstance(p, dict):
                continue
            if p.get("price") == min_price:
                w = self._weight_from_size(p.get("size", ""))
                if w:
                    return w

        for p in prices:
            if not isinstance(p, dict):
                continue
            w = self._weight_from_size(p.get("size", ""))
            if w:
                return w

        return None

    @staticmethod
    def _weight_from_size(size):
        """Извлечь вес из строки размера. Возвращает граммы или None."""
        if not isinstance(size, str):
            return None
        size = size.strip().lower()
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:кг|kg)", size)
        if m:
            return int(float(m.group(1).replace(",", ".")) * 1000)
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:гр?а?мм?|г|g)\b", size)
        if m:
            return int(float(m.group(1).replace(",", ".")))
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*л(?:ит(?:р(?:а|ов)?)?)?\b", size)
        if m:
            return int(float(m.group(1).replace(",", ".")) * 1000)
        return None
