# -*- coding: utf-8 -*-
"""ninja_food.py — парсер Ninja Food (ninjafood.su).

HTTP: главная — 224 карточки товаров (div.catalog_element), вес на сайте
только на странице товара: JS-объект BITRUCK с 'OFFERS': [{...}] — каждый
вариант (размер) имеет NAME, PRICE и DISPLAY_PROPERTIES с <dt>Вес</dt><dd>N</dd>.
Поэтому: 1) главная → список (url, название), 2) параллельно страницы товаров
→ офферы (варианты) с ценой и весом. HTTP-only, Playwright не нужен.
"""

import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client
from combo_mcp.chains.extra_utils import fetch_text, find_promos, source


class _RateGate:
    """Общий адаптивный рейт-лимит между потоками.

    Пауза перед каждым запросом растёт при неудачах (рейт-лимит сайта)
    и плавно спадает при успехах. Защита от бана при параллельном обходе.
    """

    def __init__(self, min_delay=0.15, max_delay=2.5):
        self._lock = threading.Lock()
        self._delay = min_delay
        self._min = min_delay
        self._max = max_delay
        self._consecutive_failures = 0

    def wait(self):
        with self._lock:
            d = self._delay
        time.sleep(d)

    def report(self, ok):
        with self._lock:
            if ok:
                self._consecutive_failures = 0
                self._delay = max(self._min, self._delay * 0.7)
            else:
                self._consecutive_failures += 1
                self._delay = min(self._max, self._delay * 1.6)


@chain("ninja_food")
class NinjaFoodParser(ChainParser):
    """Ninja Food — Bitrix-сайт. HTTP-only, веса со страниц товаров (OFFERS)."""

    id = "ninja_food"
    name = "Ниндзя Фуд"
    city = "Воронеж"
    url = "https://ninjafood.su/"
    description = "Bitrix-сайт. Пицца, роллы, сеты, вок, ланчи."
    needs_playwright = False

    _WORKERS = 2
    _PAGE_ATTEMPTS = 3
    _RETRY_ATTEMPTS = 5
    _RETRY_DELAY = 3.0

    def parse(self):
        """Распарсить меню Ninja Food: главная → карточки, страницы → веса."""
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        html = http_client.fetch_html(url, chain_cfg)
        if html is None or len(html) < 10000:
            raise ChainUnavailable(
                "Ninja Food недоступен: HTTP не вернул HTML. "
                "Последняя попытка: " + url
            )

        cards = self._parse_cards(html)
        if not cards:
            raise ChainUnavailable("Ninja Food: на главной не найдено карточек товаров.")

        gate = _RateGate()
        products = []
        with ThreadPoolExecutor(max_workers=self._WORKERS) as ex:
            for offers in ex.map(lambda c: self._parse_product_page(c, chain_cfg, gate=gate), cards):
                products.extend(offers)

        # Последовательный повтор по страницам, которые не ответили (анти-рейт-лимит)
        missed = [o.get("product_url") for o in products
                  if not o.get("weight_g") and o.get("product_url")]
        if missed:
            urls_to_retry = sorted(set(missed))
            for u in urls_to_retry:
                card = next((c for c in cards if c["url"] == u), None)
                if card is None:
                    continue
                offers = self._parse_product_page(card, chain_cfg, gate=gate,
                                                  retry_attempts=self._RETRY_ATTEMPTS)
                retried = any(o.get("weight_g") for o in offers)
                if retried:
                    for o in offers:
                        if o.get("weight_g"):
                            products.append(o)
                time.sleep(self._RETRY_DELAY)
        return products

    # ------------------------------------------------------------------ #
    def _parse_cards(self, html):
        """Карточки с главной: список {name, url, category, price_rub}."""
        soup = BeautifulSoup(html, "html.parser")
        cards = []
        seen = set()
        for card in soup.find_all("div", class_=True):
            cls = str(card.get("class") or [])
            if "catalog_element" not in cls:
                continue

            pid = card.get("data-id") or ""
            if not pid:
                continue

            url = ""
            name = None
            for el in card.find_all(["a", "span"], class_=True):
                el_cls = str(el.get("class") or [])
                href = str(el.get("href") or "")
                if "name" in el_cls and "often_ordered" not in el_cls:
                    t = el.get_text().strip()
                    if t:
                        name = t
                if href.startswith("/catalog/") and not url:
                    url = "https://ninjafood.su" + href

            price = None
            for el in card.find_all("span", class_=True):
                el_cls = str(el.get("class") or [])
                if "new_price" in el_cls:
                    digits = re.findall(r"\d+", el.get_text() or "")
                    if digits:
                        price = int(digits[0])
                    break

            if not name or not url or url in seen:
                continue
            seen.add(url)

            m = re.match(r"^https://ninjafood\.su/catalog/([^/]+)/[^/]+/$", url)
            cards.append({
                "name": name,
                "url": url,
                "category": m.group(1) if m else "Каталог",
                "price_rub": price,
            })
        return cards

    def _parse_product_page(self, card, chain_cfg, gate=None, retry_attempts=None):
        """Страница товара → офферы (варианты) с ценой и весом.

        gate — _RateGate: пауза перед запросом и реакция на неудачи.
        """
        attempts = retry_attempts or self._PAGE_ATTEMPTS
        html = None
        for attempt in range(attempts):
            if gate:
                gate.wait()
            html = http_client.fetch_html(card["url"], chain_cfg)
            ok = html is not None and len(html) > 10000
            if gate:
                gate.report(ok)
            if ok:
                break
            time.sleep(0.7 * (attempt + 1))
        if html is None or len(html) <= 10000:
            return [self._fallback(card, "нет ответа страницы товара")]

        offers = self._extract_offers(html, card)
        if not offers:
            return [self._fallback(card, "не найден блок OFFERS")]

        products = []
        for off in offers:
            name = off["name"] or card["name"]
            products.append({
                "name": name,
                "weight_g": off["weight_g"],
                "price_rub": off["price_rub"],
                "is_from_price": off["is_from_price"],
                "description": name,
                "category": card["category"],
                "product_url": card["url"],
                "extra": {"offer_variant": bool(off["name"])},
            })
        return products

    @staticmethod
    def _fallback(card, reason):
        """Если страница товара не дала весов — позиция без веса (как раньше)."""
        return {
            "name": card["name"],
            "weight_g": None,
            "price_rub": card.get("price_rub"),
            "is_from_price": False,
            "description": f"{card['name']} ({reason})",
            "category": card["category"],
            "product_url": card["url"],
        }

    @staticmethod
    def _extract_offers(html, card):
        """Достать из HTML страницы товара список офферов:
        [{name, price_rub, weight_g, is_from_price}].
        """
        m = re.search(r"'OFFERS':\[", html)
        if not m:
            return []

        depth = 0
        i = m.end() - 1
        while i < len(html):
            if html[i] == "[":
                depth += 1
            elif html[i] == "]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        block = html[m.start():i + 1]

        offers = []
        for om in re.finditer(r"\{'ID':'\d+','NAME':'", block):
            start = om.start()
            depth = 0
            j = start
            while j < len(block):
                if block[j] == "{":
                    depth += 1
                elif block[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            chunk = block[start:j + 1]
            off = NinjaFoodParser._parse_offer_chunk(chunk, card)
            if off:
                offers.append(off)
        return offers

    @staticmethod
    def _parse_offer_chunk(chunk, card):
        name_m = re.search(r"'NAME':'((?:[^'\\]|\\.)*)'", chunk)
        price_m = re.search(r"'PRICE':'(\d+)'", chunk)
        weight_m = re.search(r"Вес<\\?/dt><dd>(\d+)<\\?/dd>", chunk)
        diff_m = re.search(r"'DISCOUNT_DIFF':'(\d+)'", chunk)
        if not name_m or not price_m:
            return None
        name = name_m.group(1).replace("\\'", "'").replace("\\/", "/").strip()
        weight = int(weight_m.group(1)) if weight_m else None
        return {
            "name": name if name and name != card["name"] else "",
            "price_rub": int(price_m.group(1)),
            "weight_g": weight,
            "is_from_price": bool(diff_m and diff_m.group(1) != "0"),
        }

    # ------------------------------------------------------------------
    # Доп. информация: доставка, лояльность, акции
    # ------------------------------------------------------------------

    DELIVERY_URL = "https://ninjafood.su/about/delivery/"
    ACTIONS_URL = "https://ninjafood.su/akcii/"

    def parse_extra(self):
        """Доставка (зоны/мин. заказ), лояльность «Путь Ниндзя», акции с промокодами."""
        cfg = mcp_config.get_chain(self.id)

        delivery = None
        dtext = fetch_text(self.DELIVERY_URL, cfg)
        if dtext:
            zones = re.findall(r"Минимальная сумма доставки (\d+)₽", dtext)
            zone_min = sorted({int(z) for z in zones})
            min_order = zone_min[0] if zone_min else None
            delivery = {
                "min_order_rub": min_order,
                "cost_rub": None,
                "free_from_rub": None,
                "time_minutes": "Вс–Чт 10:00–23:00, Пт–Сб 10:00–24:00",
                "conditions": (
                    "Минимальная сумма зависит от зоны: "
                    + (" / ".join(str(z) for z in zone_min) if zone_min else "см. карту")
                    + " ₽ (по районам). Актуальную стоимость уточняйте при оформлении."
                ),
                "source": source(self.DELIVERY_URL),
            }

        loyalty = None
        atext = fetch_text(self.ACTIONS_URL, cfg)
        if atext and "Путь Ниндзя" in atext:
            loyalty = {
                "program": "Путь Ниндзя (многоуровневая бонусная программа)",
                "details": (
                    "Уровни: Ученик (0–6999 ₽), Мастер (7000–15999 ₽), Ниндзя (16000 ₽+). "
                    "1 ниндзя-рубль = 1 ₽; оплата бонусами до 30% заказа; срок бонусов 365 дней; "
                    "начисляются при заказе через сайт/приложение/оператора, кроме наборов, "
                    "ланчей и блюд недели."
                ),
                "source": source(self.ACTIONS_URL),
            }

        promotions = []
        if atext:
            for p in find_promos(atext, max_items=10):
                promotions.append({
                    "title": p["title"],
                    "conditions": p["conditions"],
                    "valid_until": None,
                    "source": source(self.ACTIONS_URL),
                })
            if "59 минут" in atext:
                promotions.append({
                    "title": "Доставка за 59 минут",
                    "conditions": (
                        "Если не успеем за 59 минут в красную/оранжевую зону — большая пицца "
                        "1 кг в подарок (промокод в личном кабинете, 1 месяц). В заказе — "
                        "максимум 1 пицца + 1 закуска и/или напиток."
                    ),
                    "valid_until": None,
                    "source": source(self.ACTIONS_URL),
                })

        return {"delivery": delivery, "loyalty": loyalty, "promotions": promotions}