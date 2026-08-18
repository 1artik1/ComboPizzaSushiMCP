# -*- coding: utf-8 -*-
"""favorites.py — избранное комбо: сохранить/показать/удалить понравившееся.

Файл данных: cache/favorites.json (атомарная запись через tempfile + os.replace).
"""

import json
import math
import os
import tempfile
import time

from combo_mcp import cache as cache_mod

_FAV_FILE = os.path.join(cache_mod._CACHE_DIR, "favorites.json")

# Глобальное состояние (одна сессия MCP stdio)
_fav_page = 1
PAGE_SIZE = 10
_next_id_counter = 0


def _load_favorites():
    """Загрузить избранное из файла. Пустой файл/отсутствие = {items: []}."""
    if not os.path.exists(_FAV_FILE):
        return {"items": []}
    try:
        with open(_FAV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"items": []}


def _save_favorites(data):
    """Записать файл атомарно: tempfile + os.replace."""
    os.makedirs(os.path.dirname(_FAV_FILE), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp", dir=os.path.dirname(_FAV_FILE)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, _FAV_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def favorites(action="", chain_id="", label="", items="", query=""):
    """Избранное: сохранить/показать/удалить понравившееся комбо.

    action: "add" | "list" | "remove" | "clear"
    chain_id: ID сети для добавления
    label: метка избранного (автогенерация если пусто)
    items: JSON-строка массива [{name, count, price_rub, weight_g}]
    query: для list — номер страницы / "next" / "back";
           для remove — id (число) или подстрока для поиска.
    """
    if action not in ("add", "list", "remove", "clear"):
        return json.dumps(
            {"error": "action должен быть add|list|remove|clear"},
            ensure_ascii=False,
        )

    if action == "add":
        return _fav_add(chain_id, label, items)
    if action == "list":
        return _fav_list(query)
    if action == "remove":
        return _fav_remove(query)
    if action == "clear":
        return _fav_clear()

    return json.dumps(
        {"error": "action должен быть add|list|remove|clear"},
        ensure_ascii=False,
    )


def _fav_add(chain_id, label, items_str):
    """Добавить запись в избранное."""
    if not chain_id:
        return json.dumps({"error": "chain_id обязателен для add"}, ensure_ascii=False)

    # Парсим items JSON
    try:
        item_list = json.loads(items_str)
    except (json.JSONDecodeError, TypeError):
        return json.dumps(
            {"error": "items — невалидный JSON"}, ensure_ascii=False
        )
    if not isinstance(item_list, list) or len(item_list) == 0:
        return json.dumps(
            {"error": "items должен быть непустым JSON-массивом"}, ensure_ascii=False
        )

    # Валидация: count >= 1, price_rub/weight_g опциональны (int)
    parsed = []
    total_price = 0
    total_weight = 0
    has_any_price = False
    has_any_weight = False

    for it in item_list:
        name = it.get("name", "")
        count = it.get("count", 1)
        price_rub = it.get("price_rub")
        weight_g = it.get("weight_g")

        if not isinstance(count, int) or count < 1:
            return json.dumps({"error": "count должен быть целым >= 1"}, ensure_ascii=False)

        parsed.append({"name": name, "count": count})

        if price_rub is not None:
            try:
                price_rub = int(price_rub)
            except (TypeError, ValueError):
                price_rub = None
            if price_rub is not None:
                total_price += price_rub * count
                has_any_price = True

        if weight_g is not None:
            try:
                weight_g = int(weight_g)
            except (TypeError, ValueError):
                weight_g = None
            if weight_g is not None:
                total_weight += weight_g * count
                has_any_weight = True

    if has_any_price and has_any_weight and total_weight > 0:
        price_per_100g = round(total_price / total_weight * 100, 2)
    else:
        price_per_100g = None

    # Автогенерация label
    if not label:
        parts = []
        for it in parsed[:3]:
            parts.append(f"{it['name']} x{it['count']}")
        auto_label = ", ".join(parts)
        if len(auto_label) > 80:
            auto_label = auto_label[:80] + "..."
        label = auto_label

    # Уникальный id
    global _next_id_counter
    _next_id_counter += 1
    rid = int(time.time() * 1000) + _next_id_counter

    data = _load_favorites()
    new_item = {
        "id": rid,
        "chain_id": chain_id,
        "label": label,
        "added_at": time.strftime("%Y-%m-%d %H:%M"),
        "total_weight_g": total_weight if has_any_weight else 0,
        "total_price_rub": total_price if has_any_price else 0,
        "price_per_100g": price_per_100g,
        "items": parsed,
    }
    data["items"].insert(0, new_item)
    _save_favorites(data)

    return json.dumps({
        "ok": True,
        "id": rid,
        "label": label,
        "total_weight_g": total_weight if has_any_weight else 0,
        "total_price_rub": total_price if has_any_price else 0,
        "price_per_100g": price_per_100g,
        "total_items": len(data["items"]),
    }, ensure_ascii=False, indent=2)


def _fav_list(query):
    """Показать список избранного с пагинацией."""
    global _fav_page
    data = _load_favorites()
    items = data.get("items", [])
    total = len(items)

    # query: если число — номер страницы, "next"/"back" — листание
    try:
        q = int(query) if query else 0
    except (ValueError, TypeError):
        q = 0

    if q > 0:
        _fav_page = max(1, min(q, math.ceil(total / PAGE_SIZE) if total > 0 else 1))
    elif query == "next":
        _fav_page = min(_fav_page + 1, math.ceil(total / PAGE_SIZE) if total > 0 else 1)
    elif query == "back":
        _fav_page = max(_fav_page - 1, 1)

    start = (_fav_page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]

    total_pages = math.ceil(total / PAGE_SIZE) if total > 0 else 1

    return json.dumps({
        "page": _fav_page,
        "total_pages": total_pages,
        "total_items": total,
        "items": page_items,
        "hint": (
            'favorites action="list" query="next" — следующая страница, '
            'query="back" — назад, '
            'favorites action="remove" query="<id или текст>" — удалить'
        ),
    }, ensure_ascii=False, indent=2)


def _fav_remove(query):
    """Удалить запись по id (число) или подстроке в label/именах."""
    data = _load_favorites()
    items = data.get("items", [])
    removed = 0

    try:
        qid = int(query)
        # Удаляем по id
        before_len = len(items)
        data["items"] = [it for it in items if it["id"] != qid]
        removed = before_len - len(data["items"])
    except (ValueError, TypeError):
        # Удаляем по подстроке в label или именах позиций
        q_lower = query.lower()
        before_len = len(items)
        data["items"] = [
            it for it in items
            if q_lower not in it.get("label", "").lower()
            and not any(
                q_lower in it_name.lower()
                for it_name in [i.get("name", "") for i in it.get("items", [])]
            )
        ]
        removed = before_len - len(data["items"])

    _save_favorites(data)

    return json.dumps({
        "ok": True,
        "removed": removed,
        "total_items": len(data["items"]),
    }, ensure_ascii=False, indent=2)


def _fav_clear():
    """Очистить всё избранное."""
    data = _load_favorites()
    removed = len(data.get("items", []))
    data["items"] = []
    _save_favorites(data)

    return json.dumps({
        "ok": True,
        "removed": removed,
        "total_items": 0,
    }, ensure_ascii=False, indent=2)
