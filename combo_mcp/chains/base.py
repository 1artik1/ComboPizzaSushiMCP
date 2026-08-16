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

    Метод:
        parse() -> list[dict] — распарсить меню, вернуть список позиций.
    """

    id = None
    name = ""
    city = "Воронеж"
    url = ""
    description = ""
    needs_playwright = False

    @abstractmethod
    def parse(self):
        """Распарсить меню и вернуть list[dict] позиций."""
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
