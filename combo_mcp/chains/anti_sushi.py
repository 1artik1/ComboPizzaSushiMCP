# -*- coding: utf-8 -*-
"""anti_sushi.py — парсер Anti Sushi.

Перенесён из chains_other.py: ~52 позиции.
"""

import re
from bs4 import BeautifulSoup
from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client


@chain("anti_sushi")
class AntiSushiParser(ChainParser):
    """Парсер Anti Sushi — products с schema.org markup."""

    id = "anti_sushi"
    name = "Антисуши"
    city = "Воронеж"
    url = "https://anti-sushi.ru/"
    description = "Бренд-сестра Суши Даром. Пицца, роллы, суши, сеты."
    needs_playwright = False

    def _clean(self, text):
        if text is None:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def parse(self):
        """Распарсить меню Anti Sushi."""
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        try:
            html = http_client.fetch_html(url, chain_cfg)
        except Exception as e:
            raise ChainUnavailable(f"Не удалось загрузить {url}: {e}")
        if html is None:
            raise ChainUnavailable(f"Не удалось загрузить {url}")

        products = []
        soup = BeautifulSoup(html, 'html.parser')

        product_divs = soup.find_all('div', class_='product')
        for pd in product_divs[:100]:
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
            category = "Роллы/Суши"
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
                "product_url": f"{url}/{href_url}" if href_url else url,
            })

        return products
