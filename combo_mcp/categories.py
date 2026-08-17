# -*- coding: utf-8 -*-
"""categories.py — маппинг сырых категорий меню в группы комбо.

Группы: pizza, rolls, sushi, sets, noodles, snacks, desserts, drinks,
sauces, other.
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

# Маппинг сырых категорий по сетям -> группа
# Ключи — нижний регистр сырой категории, значения — группа
_CHAIN_CATEGORIES = {
    # la_pizza
    "la_pizza": {
        "обычная": "pizza",
        "гигант": "pizza",
        "римская": "pizza",
        "комбо": "sets",
    },
    # pizza_kuba
    "pizza_kuba": {
        "Пиццы": "pizza",
        "Закуски": "snacks",
        "Соусы": "sauces",
        "Напитки": "drinks",
        "Десерты": "desserts",
    },
    # ninja_food (транслит, нижний регистр)
    "ninja_food": {
        "pitstsa": "pizza",
        "rolly": "rolls",
        "sety": "sets",
        "nabory": "sets",
        "lanchi": "other",
        "vok_i_salaty": "noodles",
        "supy": "other",
        "zakuski": "snacks",
        "sousy": "sauces",
        "deserty": "desserts",
        "napitki": "drinks",
    },
    # sushi_time
    "sushi_time": {
        "Пицца": "pizza",
        "Роллы": "rolls",
        "Суши": "sushi",
        "Сеты": "sets",
        "Онигири": "sushi",
        "Лапша": "noodles",
        "Скидки": "other",
        "Супы": "other",
        "Салаты": "other",
        "Закуски": "snacks",
        "Сендвичи": "other",
        "Десерты": "desserts",
        "Соусы": "sauces",
    },
    # sushi_darom
    "sushi_darom": {
        "Горячие закуски": "snacks",
        "Салаты": "other",
        "Специи": "sauces",
        "Гарниры": "other",
        "Десерты": "desserts",
        "Онигири": "sushi",
    },
    # anti_sushi
    "anti_sushi": {
        "Роллы/Суши": "rolls",
        "Роллы": "rolls",
        "Суши": "sushi",
        "Сеты": "sets",
        "Горячее": "noodles",
        "Пицца": "pizza",
        "Закуски": "snacks",
        "Соусы": "sauces",
        "Комбо": "sets",
    },
}


def category_to_group(item, chain_id):
    """Определить группу для позиции по категории или имени.

    Для dodo: если категория «Пицца» — детект по имени.
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

    # Прямой маппинг по категории
    cat_map = _CHAIN_CATEGORIES.get(chain_id, {})
    if category in cat_map:
        return cat_map[category]

    # sushi_darom: частичное совпадение для роллов
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

    # ninja_food: частичное совпадение
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
