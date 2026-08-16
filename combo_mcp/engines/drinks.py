# -*- coding: utf-8 -*-
"""drinks.py — детекция напитков в меню сети.

Порядок: сначала категория (napitki, Напитки, drinks...), затем эвристика
по названию (лимонад, морс, сок, кола, чай, кофе, вода, смузи...).
Нет совпадений — персоны не влияют на сеть.
"""

import re

_DRINK_CATEGORIES = {"napitki", "напитки", "drinks", "напиток"}

_DRINK_PATTERNS = [
    r"лимонад|lemonade",
    r"\bморс\b|квас|kvas|сбитень",
    r"сок|juice",
    r"\bкола\b|\bcola\b|coca|pepsi|спрайт|sprite|фанта|fanta|миринда|soda",
    r"напиток|drink",
    r"чай|tea",
    r"кофе|капучино|латте|эспрессо|американо|latte|americano|cappuccino|flat white|coffee",
    r"вода|water|минералка",
    r"компот",
    r"смузи|смоуди|smoothie",
    r"бабл|bubble|боба",
    r"молочный коктейль|коктейль|milkshake",
    r"энергетик|energy",
    r"айран",
    r"мохито|mojito|cocoa|какао|ice tea|айс ти",
    r"\bдобрый\b|\bdobry\b",
    r"nectar|нектар",
    r"мультифрукт|multifruit",
    r"lemon-lime|лимон-лайм",
    r"kiwi-grapes",
    r"bonaaqua|бонаква|bona aqua",
    r"fruit drink|фруктовый напиток",
]

_DRINK_RE = re.compile("|".join(_DRINK_PATTERNS), re.IGNORECASE)


def is_drink(item):
    """True, если позиция — напиток (по категории или названию)."""
    category = (item.get("category") or "").strip().lower()
    if category in _DRINK_CATEGORIES:
        return True
    name = item.get("name") or item.get("description") or ""
    return bool(_DRINK_RE.search(name))


def find_drinks(items):
    """Все напитки из списка позиций (без мутации исходного списка)."""
    return [it for it in items if is_drink(it)]


def find_food(items):
    """Все не-напитки (еда)."""
    return [it for it in items if not is_drink(it)]