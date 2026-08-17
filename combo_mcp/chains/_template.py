# -*- coding: utf-8 -*-
"""_template.py — готовый шаблон новой сети с комментариями.

Проще: python scripts/new_chain.py <id> "<Имя>" <url>
"""

from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client


@chain("new_chain")
class NewChainParser(ChainParser):
    """Шаблон парсера новой сети доставки.

    Атрибуты:
        id:           "new_chain"
        name:         "Новая сеть"
        city:         "Воронеж"
        url:          "https://example.com/"
        description:  "Описание сети"
        needs_playwright: False  # True, если нужен browser
        category_map: {}  # {"Сырая категория": "pizza", ...}

    Метод parse() должен:
        1. Загрузить страницу через http_client.fetch_html (или playwright)
        2. Распарсить HTML/JSON и извлечь позиции
        3. Вернуть list[dict] позиций в формате:
           {
               "name": "Название",
               "weight_g": 250,      # int или None если нет на сайте
               "price_rub": 350,
               "is_from_price": False,
               "description": "Описание",
               "category": "Категория",
               "product_url": "https://...",
               "in_stock": True,
               "extra": {},
           }
    """

    id = "new_chain"
    name = "Новая сеть"
    city = "Воронеж"
    url = "https://example.com/"
    description = "Описание новой сети доставки"
    needs_playwright = False
    # category_map: сырая категория меню -> группа комбо
    # (pizza/rolls/sushi/sets/noodles/snacks/desserts/drinks/sauces/other)
    category_map = {
        # "Сырая категория": "pizza",
        # "Другая категория": "rolls",
    }

    def parse(self):
        """Распарсить меню новой сети.

        URL и таймауты берутся из config.get_chain(chain_id).
        """
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        # Загрузка страницы
        html = http_client.fetch_html(url, chain_cfg)
        if html is None:
            raise ChainUnavailable(f"Не удалось загрузить {url}")

        # TODO: распарсить HTML и вернуть позиции
        # Пример:
        # products = []
        # for item in parsed_items:
        #     products.append({
        #         "name": item["name"],
        #         "weight_g": item.get("weight"),
        #         "price_rub": item["price"],
        #         ...
        #     })
        # return products

        raise ChainUnavailable(
            f"Парсер для {self.id} не реализован. URL: {url}"
        )

    def parse_extra(self) -> dict:
        """Доп. информация о сети: доставка, лояльность, акции."""
        return {}
