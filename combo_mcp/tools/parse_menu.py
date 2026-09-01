# -*- coding: utf-8 -*-
"""parse_menu.py — parse_menu(chain_id, category, min_weight, sort_by, limit, refresh).

category: распознаётся как группы (resolve_categories: «пицца», «роллы»,
«напитки»...), при нераспознанном запросе — fallback на сырую подстроку
категории меню.
"""

import json
from combo_mcp.config import get_chain_meta
from combo_mcp.shared import fetch_items
from combo_mcp.categories import category_to_group, resolve_categories
from combo_mcp.params import to_bool, to_int, MAX_LIMIT

_VALID_SORTS = ("price", "weight", "price_per_100g")


def parse_menu(chain_id, category=None, min_weight=None, sort_by=None, limit=None, refresh=False):
    """Распарсить меню конкретной сети."""
    chain_id = (chain_id or "").strip()
    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    try:
        refresh = to_bool(refresh)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    if min_weight not in (None, ""):
        try:
            min_weight = to_int(min_weight, "min_weight", minimum=1)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    else:
        min_weight = None

    if limit not in (None, ""):
        try:
            limit = to_int(limit, "limit", minimum=1, maximum=MAX_LIMIT)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    else:
        limit = None

    if sort_by and sort_by not in _VALID_SORTS:
        return json.dumps({
            "error": f"sort_by должен быть одним из: {', '.join(_VALID_SORTS)}"
        }, ensure_ascii=False)

    items, stale, load_error = fetch_items(chain_id, refresh)
    if items is None:
        return json.dumps({"error": f"Не удалось загрузить меню: {load_error}"}, ensure_ascii=False)

    return _filter_sort(items, chain_id, category, min_weight, sort_by, limit)


def _filter_sort(items, chain_id, category, min_weight, sort_by, limit):
    """Фильтр и сортировка.

    category: сначала попытка распознать группы; если не распознана ни одна —
    fallback на сырую подстроку category поля меню.
    """
    selected_groups = resolve_categories(category) if category else ()
    cat_lower = category.strip().lower() if category and category.strip() \
        else ""
    grp = "other"

    result = []
    for it in items:
        if category:
            grp = category_to_group(it, chain_id)
            if selected_groups:
                if grp not in selected_groups:
                    continue
            elif cat_lower not in (it.get("category") or "").lower():
                continue
        if min_weight and it.get("weight_g") is not None and it["weight_g"] < min_weight:
            continue
        entry = dict(it)
        if selected_groups:
            entry["group"] = grp
        result.append(entry)

    if sort_by == "price_per_100g":
        result.sort(key=lambda x: x["price_rub"] / x["weight_g"] if x.get("weight_g") and x["weight_g"] > 0 else float('inf'))
    elif sort_by == "price":
        result.sort(key=lambda x: x["price_rub"])
    elif sort_by == "weight":
        result.sort(key=lambda x: x["weight_g"] if x.get("weight_g") else 0, reverse=True)

    if limit:
        result = result[:limit]

    return json.dumps(result, ensure_ascii=False, indent=2)