# -*- coding: utf-8 -*-
"""names.py — локализация названий и подпись размера единицы товара.

- localize(chain_id, name): перевод названия через config/translations.json
  (оригинальные/брендовые названия остаются как есть — их нет в словаре).
- item_size_label(item): подпись единицы для вывода в комбо:
    * справочный вес с указанием штук: "9 шт, 20 г/шт" (из weight_source_name)
    * иначе: "1000 г"
  Пустая строка, если веса нет.
"""

import json
import os
import re

_TRANSLATIONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "translations.json",
)

_translations = None


def load_translations():
    """Словарь переводов: {"<chain_id>": {"<имя>": "<перевод>"}}."""
    global _translations
    if _translations is None:
        try:
            with open(_TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
                _translations = json.load(f)
        except (OSError, ValueError):
            _translations = {}
    return _translations


def localize(chain_id, name):
    """Русское название позиции или оригинал, если перевода нет."""
    if not name:
        return name
    tr = load_translations().get(chain_id, {}).get(name)
    return tr if tr else name


_PCS_RE = re.compile(r"(\d+)\s*шт[^0-9]*~?\s*(\d+)\s*г\s*/?\s*шт")


def item_size_label(item):
    """Подпись размера/веса единицы: "(9 шт, 20 г/шт)" или "(1000 г)"."""
    w = item.get("weight_g")
    if not w or w <= 0:
        return ""
    source = item.get("weight_source_name") or ""
    if item.get("weight_source") == "reference" and source:
        m = _PCS_RE.search(source)
        if m:
            return f"{m.group(1)} шт, {m.group(2)} г/шт"
    return f"{w} г"