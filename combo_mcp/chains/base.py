# -*- coding: utf-8 -*-
"""base.py — ChainParser: абстрактный базовый класс + декоратор @chain()."""

from abc import ABC, abstractmethod


class ChainUnavailable(Exception):
    """Исключение при недоступности сети."""

    pass


class ChainParser(ABC):
    """Базовый класс для парсеров сетей доставки.

    Атрибуты:
        id:           идентификатор сети (la_pizza, sushi_darom, ...)
        name:         отображаемое имя
        city:         город
        url:          базовый URL
        description:  описание сети
        needs_playwright: True, если нужен browser для парсинга
        category_map: {сырая_категория: группа} — маппинг категорий меню

    Метод:
        parse() -> list[dict] — распарсить меню, вернуть список позиций.
    """

    id = None
    name = ""
    city = "Воронеж"
    url = ""
    description = ""
    needs_playwright = False
    # category_map: сырая категория меню -> группа комбо
    # (pizza/rolls/sushi/sets/noodles/snacks/desserts/drinks/sauces/other)
    category_map = {}
    # has_server_search: True если у парсера рабочий серверный поиск (magnit/pyaterochka)
    has_server_search = False

    @abstractmethod
    def parse(self):
        """Распарсить меню и вернуть list[dict] позиций."""
        raise NotImplementedError

    def parse_extra(self) -> dict:
        """Доп. информация о сети: доставка, лояльность, акции.

        Вернуть dict: {"delivery": {...}|None, "loyalty": {...}|None,
        "promotions": [...]} или None, если не реализовано.
        """
        return {}

    def search(self, query, limit=20):
        """Сервисный поиск товаров по запросу.

        Возвращает list[dict] позиций (такой же формат, как parse()).
        Дефолт — NotImplementedError (переопределяют magnit/pyaterochka).
        """
        raise NotImplementedError

    def get_categories(self):
        """Сервисное получение дерева категорий сервера.

        Возвращает list[dict] категорий.
        Дефолт — NotImplementedError (переопределяют magnit/pyaterochka).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Декоратор @chain("id")
# ---------------------------------------------------------------------------

_REGISTRY = {}


def chain(chain_id):
    """Декоратор для регистрации chain-класса в реестре.

    Usage:
        @chain("sushi_darom")
        class SushiDaromParser(ChainParser):
            id = "sushi_darom"
            name = "Суши Даром"
            ...
    """

    def decorator(cls):
        cls.id = chain_id
        _CHAIN_REGISTRY[chain_id] = cls
        return cls

    return decorator


_CHAIN_REGISTRY = {}


def get_chain_class(chain_id):
    """Получить класс парсера по id."""
    return _CHAIN_REGISTRY.get(chain_id)


def get_all_chains():
    """Получить все зарегистрированные chain-классы."""
    return dict(_CHAIN_REGISTRY)
