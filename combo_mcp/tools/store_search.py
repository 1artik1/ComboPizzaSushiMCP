# -*- coding: utf-8 -*-
"""store_search.py — поиск товаров только по магазинам (kind=store).

store_search(query, store, ...) ищет товары через нативный серверный поиск
магазина (parser.search), а не через меню-кэш: свежие цены и наличие.
Рестораны (kind=combo) здесь не участвуют — для них есть parse_menu/best_combo.
Отключённый магазин (enabled=false), например Пятёрочка (анти-бот, API 403), —
явная ошибка. Use: store_search("молоко"), store_search("хлеб", store="magnit").
"""

import json

from combo_mcp.config import get_chain_meta, get_chain_class, get_store_chain_ids, get_chain_kind
from combo_mcp.params import to_int, to_float, to_bool
from combo_mcp.engines.textmatch import score_match
from combo_mcp.chains.base import ChainUnavailable

_SORTS = ("relevance", "price_asc", "price_desc")


def _err(msg):
    return json.dumps({"error": msg}, ensure_ascii=False)


def _normalize_item(it):
    """Привести позицию поискового API к единому формату ответа."""
    return {
        "name": it.get("name", ""),
        "price_rub": it.get("price_rub"),
        "weight_g": it.get("weight_g"),
        "weight_source": it.get("weight_source", ""),
        "category": it.get("category", ""),
        "in_stock": it.get("in_stock"),
    }


def store_search(
    query,
    store="",
    min_price="",
    max_price="",
    in_stock="true",
    sort="relevance",
    limit="20",
):
    """Поиск товаров по включённым магазинам (store="" — все) или выбранным."""
    if not query or not query.strip():
        return _err("Не указан query (поисковый запрос)")

    try:
        limit_val = to_int(limit, "limit", minimum=1, maximum=500)
    except ValueError as e:
        return _err(str(e))

    try:
        in_stock_val = to_bool(in_stock, default=True)
    except ValueError as e:
        return _err(str(e))

    try:
        min_val = (
            to_float(min_price, "min_price", minimum=0)
            if str(min_price).strip()
            else None
        )
        max_val = (
            to_float(max_price, "max_price", minimum=0)
            if str(max_price).strip()
            else None
        )
    except ValueError as e:
        return _err(str(e))
    if min_val is not None and max_val is not None and max_val < min_val:
        return _err(f"max_price ({max_val}) меньше min_price ({min_val})")

    sort_val = (sort or "").strip().lower()
    if sort_val not in _SORTS:
        return _err(f"Неизвестная сортировка '{sort}'. Доступны: {', '.join(_SORTS)}")

    store_ids = get_store_chain_ids()
    meta = {c["id"]: c for c in get_chain_meta()}

    raw = (store or "").strip()
    if not raw:
        targets = list(store_ids)
    else:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        unknown = [p for p in parts if p not in meta]
        if unknown:
            return _err(
                f"Неизвестный магазин '{unknown[0]}'. "
                f"Доступны: {', '.join(sorted(meta))}"
            )
        disabled = [p for p in parts if p in meta and p not in store_ids
                    and get_chain_kind(p) == "store"]
        not_store = [p for p in parts if p in meta and p not in store_ids
                     and get_chain_kind(p) != "store"]
        if disabled:
            return _err(
                f"'{', '.join(disabled)}' — магазин, но отключён (enabled=false). "
                f"Доступные магазины: {', '.join(sorted(store_ids)) or 'нет'}"
            )
        if not_store:
            return _err(
                f"'{', '.join(not_store)}' — не магазин (kind=combo). "
                f"Для ресторанов используйте parse_menu/best_combo/compare."
            )
        targets = [p for p in parts if p in store_ids]

    has_price_bounds = min_val is not None or max_val is not None

    results = []
    stores_errors = {}

    for cid in targets:
        cls = get_chain_class(cid)
        if cls is None or not getattr(cls, "has_server_search", False):
            stores_errors[cid] = "у магазина нет серверного поиска"
            continue
        try:
            items = cls().search(query, limit=limit_val) or []
        except ChainUnavailable as e:
            stores_errors[cid] = str(e)
            continue
        except Exception as e:
            stores_errors[cid] = f"search error: {e}"
            continue

        chain_name = meta.get(cid, {}).get("name", cid)
        for it in items:
            if it.get("price_rub") is None:
                continue
            if has_price_bounds:
                price = it.get("price_rub")
                if min_val is not None and price < min_val:
                    continue
                if max_val is not None and price > max_val:
                    continue
            if in_stock_val and it.get("in_stock") is False:
                continue
            norm = _normalize_item(it)
            norm["chain_id"] = cid
            norm["chain_name"] = chain_name
            norm["score"] = score_match(query, norm["name"], norm["category"])
            results.append(norm)

    if sort_val == "price_asc":
        results.sort(key=lambda x: (x["price_rub"] is None, x["price_rub"], x["chain_id"], x["name"]))
    elif sort_val == "price_desc":
        results.sort(key=lambda x: (x["price_rub"] is None, -x["price_rub"], x["chain_id"], x["name"]))
    else:
        results.sort(key=lambda x: (-x["score"], x["chain_id"], x["name"]))

    return json.dumps(
        {
            "query": query,
            "stores_searched": targets,
            "sort": sort_val,
            "limit": limit_val,
            "total": len(results),
            "results": results[:limit_val],
            "stores_errors": stores_errors,
        },
        ensure_ascii=False,
        indent=2,
    )