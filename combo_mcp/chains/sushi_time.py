# -*- coding: utf-8 -*-
"""sushi_time.py — парсер Sushi Time (sushi-time.рф).

HTTP: HTML 1.9MB, 251 product card (div.tovar_small).
- div.tovar_small: data-id (product ID)
- div.tovar_small > ... > a.linknoactive: data-title (name), data-category-name (category)
- span#vess_preview_<id>: weight "900 гр" → weight_g
- div.price_preview (inside tovar_small): "650 ₽900 ₽" → price_rub (first number before ₽)
- Вес: из span#vess_preview_<id> (237 вхождений)
- Цена: из div.price_preview (251 вхождение, все товары)
- JSON-LD в HTML закомментирован — парсим DOM-атрибуты напрямую.
"""

import re
from bs4 import BeautifulSoup
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client
from combo_mcp.chains.extra_utils import fetch_text, source


@chain("sushi_time")
class SushiTimeParser(ChainParser):
    """Sushi Time — сайт на IDN домене. HTTP-only, DOM-атрибуты."""

    id = "sushi_time"
    name = "Сушитайм"
    city = "Воронеж"
    url = "https://xn----8sbwgpzjf9b.xn--p1ai/Voronezh/"
    description = "Доставка роллов и суши. IDN-домен."
    needs_playwright = False

    def parse(self):
        """Распарсить меню Sushi Time из HTML."""
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        html = http_client.fetch_html(url, chain_cfg)
        if html is None or len(html) < 10000:
            raise ChainUnavailable(
                "Sushi Time недоступен: HTTP не вернул HTML. "
                "Последняя попытка: " + url
            )

        return self._parse_html(html)

    def _parse_html(self, html):
        """Parse products from HTML using BS4 DOM."""
        soup = BeautifulSoup(html, "html.parser")

        # --- Find all tovar_small divs ---
        products = []
        for card in soup.find_all("div", class_=True):
            cls = str(card.get("class") or [])
            if "tovar_small" not in cls:
                continue

            pid = card.get("data-id") or ""
            if not pid:
                continue

            # Find <a> with data-title inside this card
            for a in card.find_all("a", attrs={"data-title": True}):
                title = a.get("data-title") or ""
                cat = a.get("data-category-name") or ""
                if isinstance(title, str) and title.strip():
                    name = title.strip()
                    category = cat.strip() if isinstance(cat, str) and cat.strip() else "Роллы/Суши"

                    # Find weight from span#vess_preview_<pid>
                    weight = None
                    weight_span = card.find("span", id=f"vess_preview_{pid}")
                    if weight_span:
                        wt_text = weight_span.get_text() or ""
                        m = re.search(r"(\d+)\s*[гг]", wt_text)
                        if m:
                            weight = int(m.group(1))

                    # Find price from div.price_preview inside this card
                    price = None
                    for pd in card.find_all("div", class_=True):
                        pd_cls = str(pd.get("class") or [])
                        if "price_preview" in pd_cls:
                            text = pd.get_text() or ""
                            # "1 300 ₽" → 1300 (handle space-separated thousands)
                            m = re.search(r'(\d+(?:\s+\d+)?)\s*₽', text)
                            if m:
                                price = int(m.group(1).replace(' ', ''))
                            break

                    products.append({
                        "name": name,
                        "weight_g": weight,
                        "price_rub": price,
                        "is_from_price": False,
                        "description": name,
                        "category": category,
                        "product_url": "",
                    })
                break

        return products

    # ------------------------------------------------------------------
    # Доп. информация: доставка (зоны), лояльность «Таймы», акции
    # ------------------------------------------------------------------

    BASE = "https://xn----8sbwgpzjf9b.xn--p1ai/Voronezh"
    DELIVERY_URL = BASE + "/dostavka"
    SALE_URL = BASE + "/sale"
    POINTS_URL = BASE + "/points"

    def parse_extra(self):
        """Доставка по зонам, бонусы «Таймы», акции."""
        cfg = mcp_config.get_chain(self.id)

        delivery = None
        dtext = fetch_text(self.DELIVERY_URL, cfg)
        if dtext:
            zones = re.findall(
                r"в ([А-ЯЁа-яё]+) зоне доставки:\s*минимальная сумма заказа - (\d+) руб\.\s*"
                r"при заказе от (\d+) руб\. - доставка бесплатно;\s*"
                r"при заказе менее \d+ руб\. - сумма доставки (\d+) руб\.",
                dtext,
            )
            parts = []
            for z, mn, free, cost in zones:
                parts.append(
                    f"{z}: мин. {mn} ₽, бесплатно от {free} ₽, иначе {cost} ₽"
                )
            if not parts:
                parts = ["См. условия на сайте"]
            delivery = {
                "min_order_rub": 500,
                "cost_rub": 150,
                "free_from_rub": 800,
                "time_minutes": "10:00–22:00",
                "conditions": (
                    "Зоны доставки: "
                    + "; ".join(parts[:6])
                    + ". Заказы от 3000 ₽ — по предоплате. "
                    "Доставка ко времени ±20 минут."
                ),
                "source": source(self.DELIVERY_URL),
            }

        loyalty = None
        ptext = fetch_text(self.POINTS_URL, cfg)
        if ptext and "Таймы" in ptext:
            loyalty = {
                "program": "Таймы (бонусная программа)",
                "details": (
                    "Возвращаем 3% от каждой покупки бонусами; оплата до 50% заказа; "
                    "бонусы не сгорают; начисляются только за онлайн-заказы (сайт, "
                    "приложения); при отмене заказа не начисляются; на заказ, оплаченный "
                    "бонусами, новые бонусы не начисляются."
                ),
                "source": source(self.POINTS_URL),
            }

        promotions = []
        stext = fetch_text(self.SALE_URL, cfg)
        if stext:
            known = [
                ("250 ₽ за фотоотзыв", "Дарим 250₽ за фотоотзыв в группе VK",
                 "Промокод на скидку 250 ₽ к заказу от 1100 ₽. Суммируется со скидками.", None),
                ("Скидка 10% на день рождения", "Автоматическая скидка на День Рождения",
                 "Скидка 10% в день рождения, заполни дату в личном кабинете. "
                 "Акции и скидки не суммируются.", None),
                ("Подарки к каждому заказу", "Подарки к каждому заказу!",
                 "Выбирай 1 из 3 подарков по шкале корзины — чем больше заказ, тем лучше подарок.", None),
                ("Обед за 280 ₽", "Обедай вместе с Суши Тайм за 280₽",
                 "С понедельника по пятницу с 10:00 до 15:00. Акции и скидки не суммируются.", None),
            ]
            for title, marker, cond, until in known:
                if marker[:24] in stext:
                    promotions.append({
                        "title": title, "conditions": cond,
                        "valid_until": until, "source": source(self.SALE_URL),
                    })

        return {"delivery": delivery, "loyalty": loyalty, "promotions": promotions}
