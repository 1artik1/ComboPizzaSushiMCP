# -*- coding: utf-8 -*-
"""anti_sushi.py — парсер Anti Sushi.

Перенесён из chains_other.py: ~52 позиции + подкаталоги (пицца, фьюжен, соусы,
комбо, спецпредложения) ≈ 110 позиций.
Напитки: /catalog/drinks/ → 404, категория удалена с сайта.
"""

import re
from bs4 import BeautifulSoup
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client
from combo_mcp.chains.extra_utils import fetch_text, find_promos, source


@chain("anti_sushi")
class AntiSushiParser(ChainParser):
    """Парсер Anti Sushi — products с schema.org markup.

    Парсит главную страницу (роллы, суши, сеты, горячее, закуски) +
    подкаталоги из навигации: пицца, фьюжен, соусы, комбо, спецпредложения.
    """

    id = "anti_sushi"
    name = "Антисуши"
    city = "Воронеж"
    url = "https://anti-sushi.ru/"
    description = "Бренд-сестра Суши Даром. Пицца, роллы, суши, сеты."
    needs_playwright = False
    category_map = {
        "Роллы/Суши": "rolls",
        "Роллы": "rolls",
        "Суши": "sushi",
        "Сеты": "sets",
        "Горячее": "noodles",
        "Пицца": "pizza",
        "Закуски": "snacks",
        "Соусы": "sauces",
        "Комбо": "combo",
    }

    DELIVERY_URL = "https://anti-sushi.ru/delivery/"
    SALES_URL = "https://anti-sushi.ru/sales/"

    # Подкаталоги с навигации главной страницы
    SUB_CATALOGS = [
        ("/catalog/pitstsa/", "Пицца"),
        ("/catalog/fusion/", "Фьюжен"),
        ("/catalog/sauces/", "Соусы"),
        ("/catalog/kombo/", "Комбо"),
        ("/catalog/special-offers/", "Спецпредложения"),
    ]

    def _clean(self, text):
        if text is None:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    # ------------------------------------------------------------------
    # Парсинг одной страницы (главная или подкаталог)
    # ------------------------------------------------------------------

    def _parse_products_from_html(self, html, default_category="Роллы/Суши"):
        """Распарсить div.product с schema.org markup из HTML.

        Возвращает список dict-позиций.
        """
        products = []
        soup = BeautifulSoup(html, 'html.parser')

        product_divs = soup.find_all('div', class_='product')
        for pd in product_divs:
            price_meta = pd.find('meta', itemprop='price')
            if not price_meta:
                continue
            try:
                price = int(price_meta['content'])
            except (ValueError, KeyError):
                continue
            if price <= 0:
                continue

            name_meta = pd.find('meta', itemprop='name')
            if not name_meta:
                continue
            name = self._clean(name_meta['content'])
            if not name or len(name) < 3:
                continue

            weight = None
            weight_span = pd.find('span', class_='weight')
            if weight_span:
                wt_text = self._clean(weight_span.get_text())
                wt_num = re.search(r'(\d+)', wt_text)
                if wt_num:
                    weight = int(wt_num.group(1))

            desc_div = pd.find('div', class_='product-description')
            description = self._clean(desc_div.get_text()) if desc_div else name

            href = pd.find('a', class_='product-title')
            category = default_category
            href_url = ""
            if href and href.get('href'):
                href_url = href['href']
                cat_url = href_url.lower()
                if 'sets' in cat_url or 'сеты' in cat_url:
                    category = "Сеты"
                elif 'rolls' in cat_url or 'ролл' in cat_url:
                    category = "Роллы"
                elif 'sushi' in cat_url or 'суши' in cat_url:
                    category = "Суши"
                elif 'pizza' in cat_url or 'пицца' in cat_url:
                    category = "Пицца"
                elif 'lapsha' in cat_url or 'лапша' in cat_url:
                    category = "Горячее"
                elif 'zakuski' in cat_url or 'закус' in cat_url:
                    category = "Закуски"

            products.append({
                "name": name,
                "weight_g": weight,
                "price_rub": price,
                "is_from_price": False,
                "description": description,
                "category": category,
                "product_url": f"{self.url}/{href_url}" if href_url else self.url,
            })

        return products

    # ------------------------------------------------------------------
    # Основной метод parse
    # ------------------------------------------------------------------

    def parse(self):
        """Распарсить меню Anti Sushi (главная + подкаталоги)."""
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        # 1. Главная страница (роллы, суши, сеты, горячее, закуски)
        products = []
        try:
            html = http_client.fetch_html(url, chain_cfg)
            if html:
                products = self._parse_products_from_html(html, default_category="Роллы/Суши")
        except Exception:
            pass

        # 2. Подкаталоги из навигации
        for cat_path, cat_name in self.SUB_CATALOGS:
            try:
                cat_url = f"{url}{cat_path}"
                cat_html = http_client.fetch_html(cat_url, chain_cfg)
                if cat_html:
                    sub = self._parse_products_from_html(cat_html, default_category=cat_name)
                    products.extend(sub)
            except Exception:
                pass

        # 3. Дедупликация по имени
        seen = set()
        deduped = []
        for p in products:
            key = p["name"]
            if key not in seen:
                seen.add(key)
                deduped.append(p)

        return deduped

    # ------------------------------------------------------------------
    # Доп. информация: доставка, бонусы, акции с промокодами
    # ------------------------------------------------------------------

    def parse_extra(self):
        """Доставка (карта/зоны), бонусные рубли, акции с промокодами."""
        cfg = mcp_config.get_chain(self.id)

        delivery = None
        dtext = fetch_text(self.DELIVERY_URL, cfg)
        if dtext:
            delivery = {
                "min_order_rub": None,
                "cost_rub": None,
                "free_from_rub": None,
                "time_minutes": "10:00–24:00, от 45 минут",
                "conditions": (
                    "Стоимость доставки и минимальный заказ зависят от района (на карте "
                    "сайта, в некоторые районы — бесплатно); заказы от 3000 ₽ — предоплата "
                    "50%; курьер ожидает не более 10 минут, повторный довоз платный; "
                    "минимальный заказ на доставку — 750 ₽."
                ),
                "source": source(self.DELIVERY_URL),
            }

        loyalty = None
        stext = fetch_text(self.SALES_URL, cfg)
        if stext and "можно оплачивать" in stext.lower():
            loyalty = {
                "program": "Бонусные рубли",
                "details": (
                    "1 бонус = 1 ₽; оплата до 30% заказа; начисление: 3% с первого заказа, "
                    "5% после 5000 ₽, 10% после 10000 ₽ (сумма заказов за 6 месяцев); "
                    "бонусы не начисляются с акционных товаров; списание недоступно при "
                    "использовании промокода на акцию."
                ),
                "source": source(self.SALES_URL),
            }

        promotions = []
        if stext:
            for p in find_promos(stext, max_items=12):
                promotions.append({
                    "title": p["title"],
                    "conditions": p["conditions"],
                    "valid_until": None,
                    "source": source(self.SALES_URL),
                })
            known = [
                ("Подарок в день рождения", "Подарок в день рождения",
                 "Заказ от 1500 ₽: сет «Умамини» или пицца «Ранчо» 25 см, ±3 дня от ДР, "
                 "единоразово, предъявить паспорт."),
                ("Бонусы за отзывы", "Бонусы отзывчивым",
                 "100 бонусов за текстовый отзыв, 200 за фото (Яндекс/Google/Отзовик/2GIS/VK), "
                 "указать номер заказа."),
                ("Опоздали — пицца в подарок", "Привезем вовремя или пицца в подарок",
                 "Если заказ опоздал более чем на 15 минут — пицца в подарок к следующему "
                 "заказу от 999 ₽; пн–чт; не действует на заказы свыше 3000 ₽."),
            ]
            for title, marker, cond in known:
                if marker in stext:
                    promotions.append({
                        "title": title, "conditions": cond,
                        "valid_until": None, "source": source(self.SALES_URL),
                    })

        return {"delivery": delivery, "loyalty": loyalty, "promotions": promotions}
