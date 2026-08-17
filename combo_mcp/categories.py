# -*- coding: utf-8 -*-
"""categories.py — маппинг сырых категорий меню в группы комбо.

Группы: pizza, rolls, sushi, sets, noodles, snacks, desserts, drinks,
sauces, other.

Маппинг берётся из атрибута category_map класса парсера (chain.py),
fallback — эвристики для sushi_darom / anti_sushi / ninja_food.
"""

import re
from combo_mcp.engines.drinks import is_drink as _is_drink

# Группы
ALL_GROUPS = [
    "pizza", "rolls", "sushi", "sets", "noodles",
    "snacks", "desserts", "drinks", "sauces", "other",
]

# Синонимы: нижний регистр -> группа
_SYNONYMS = {
    "пицц": "pizza", "pizza": "pizza",
    "ролл": "rolls", "rolls": "rolls",
    "суши": "sushi", "sushi": "sushi",
    "сет": "sets", "sets": "sets", "набор": "sets", "комбо": "sets",
    "лапша": "noodles", "noodles": "noodles", "вок": "noodles",
    "закуск": "snacks", "snacks": "snacks",
    "десерт": "desserts", "desserts": "desserts",
    "напитк": "drinks", "drinks": "drinks", "napitki": "drinks",
    "сок": "drinks", "вода": "drinks", "кола": "drinks",
    "соус": "sauces", "sauces": "sauces", "сousy": "sauces",
}


def _chain_category_map(chain_id):
    """category_map класса парсера сети ({} если парсера нет)."""
    try:
        from combo_mcp.chains.base import get_chain_class
        cls = get_chain_class(chain_id)
        if cls is None:
            return {}
        return getattr(cls, "category_map", {})
    except Exception:
        return {}


def category_to_group(item, chain_id):
    """Определить группу для позиции по категории или имени.

    Для dodo: если категория «Пицца» — детект по имени (напитки, десерты).
    Для остальных: берём category_map класса парсера, затем fallback-эвристики.
    """
    name = (item.get("name") or "").lower()
    category = (item.get("category") or "").strip()

    # dodo: все в категории «Пицца», детект по имени
    # Напитки имеют приоритет: milkshake, juice drink и т.д. могут содержать
    # dessert-слова, но это напитки
    if chain_id == "dodo":
        if _is_drink(item):
            return "drinks"
        dessert_patterns = [
            "chocolate", "cheesecake", "muffin", "cookie", "brownie",
            "cake", "bomboni", "бомбони", "waffle", "donut", "десерт",
        ]
        if any(w in name for w in dessert_patterns):
            return "desserts"
        return "pizza"

    # Прямой маппинг по category_map класса парсера
    cat_map = _chain_category_map(chain_id)
    if category in cat_map:
        return cat_map[category]

    # sushi_darom: частичное совпадение для роллов/сетов/суши/онигири
    if chain_id == "sushi_darom":
        cat_lower = category.lower()
        if "ролл" in cat_lower:
            return "rolls"
        if cat_lower in ("сеты", "сеты -70%", "наборы"):
            return "sets"
        if "суши" in cat_lower:
            return "sushi"
        if "онигири" in cat_lower:
            return "sushi"

    # anti_sushi: частичное совпадение
    if chain_id == "anti_sushi":
        cat_lower = category.lower()
        if "ролл" in cat_lower:
            return "rolls"
        if "суши" in cat_lower:
            return "sushi"

    # ninja_food: частичное совпадение ключа в категории
    if chain_id == "ninja_food":
        cat_lower = category.lower()
        for key, group in cat_map.items():
            if key in cat_lower:
                return group

    return "other"


def resolve_categories(query):
    """Разобрать строку запроса в список уникальных групп.

    query — строка с группами/синонимами через запятую или пробел.
    Возвращает уникальный список групп; если ни одно слово не распознано — [].
    """
    if not query or not query.strip():
        return []

    words = re.split(r"[,\s]+", query.strip().lower())
    # Убираем пустые слова
    words = [w for w in words if w]

    found = set()
    for word in words:
        # Прямое совпадение с группой
        if word in ALL_GROUPS:
            found.add(word)
        # Прямое совпадение с синонимом
        if word in _SYNONYMS:
            found.add(_SYNONYMS[word])
        # Подстрока: синоним содержится в слове
        for syn, grp in _SYNONYMS.items():
            if syn in word:
                found.add(grp)

    return sorted(found)
