# -*- coding: utf-8 -*-
"""search_products.py — универсальный поиск продукции для нейросети.

search_products(query, ...) ищет по меню всех сетей сразу или в выбранных
(stores="magnit,la_pizza" / chain_id=): нормализация (регистр/ё/пунктуация),
опечатки в 1 букву (Левенштейн для слов от 5 символов), фильтры цены/
категорий/наличия, сортировка по релевантности или цене. Источник данных —
всегда fetch_items (TTL-кэш + stale-if-error).
"""

import json

from combo_mcp.config import get_chain_meta, get_enabled_chain_ids
from combo_mcp.shared import fetch_items
from combo_mcp.params import to_int, to_bool, to_float
from combo_mcp.categories import category_to_group, resolve_categories
from combo_mcp.engines.textmatch import normalize, score_match

_SORTS = ("relevance", "price_asc", "price_desc")


def _err(msg):
    return json.dumps({"error": msg}, ensure_ascii=False)


def _parse_stores(stores, known_ids):
    """Разобрать stores в список id: ''/'all' → включённые сети; иначе CSV.

    Возвращает (chain_ids, error): error не None при неизвестном магазине.
    Дедупликация с сохранением порядка.
    """
    s = (stores or "").strip()
    if not s or s.lower() == "all":
        return list(get_enabled_chain_ids()), None
    out, seen = [], set()
    for part in s.split(","):
        cid = part.strip()
        if not cid or cid in seen:
            continue
        if cid not in known_ids:
            return None, (
                f"Неизвестный магазин '{cid}'. Доступны: {', '.join(sorted(known_ids))}"
            )
        seen.add(cid)
        out.append(cid)
    if not out:
        return None, (f"Не указаны магазины. Доступны: {', '.join(sorted(known_ids))}")
    return out, None


def search_products(
    query,
    chain_id="",
    stores="all",
    categories="",
    min_price="",
    max_price="",
    in_stock="true",
    sort="relevance",
    limit="20",
    refresh="false",
):
    """Поиск продукции сразу по всем магазинам или в выбранных."""
    if not query or not query.strip():
        return _err("Не указан query (поисковый запрос)")

    try:
        limit_val = to_int(limit, "limit", minimum=1)
    except ValueError as e:
        return _err(str(e))

    try:
        refresh_val = to_bool(refresh)
        in_stock_val = to_bool(in_stock)
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

    known_ids = [c["id"] for c in get_chain_meta()]
    if chain_id:
        if chain_id not in known_ids:
            return _err(
                f"Неизвестная сеть '{chain_id}'. "
                f"Доступны: {', '.join(sorted(known_ids))}"
            )
        chain_ids = [chain_id]
    else:
        chain_ids, stores_err = _parse_stores(stores, known_ids)
        if stores_err is not None or chain_ids is None:
            return _err(stores_err or "Не указаны магазины")

    meta = {c["id"]: c for c in get_chain_meta()}

    # Категорийный фильтр: группы из resolve_categories, иначе подстрока
    cat_groups = resolve_categories(categories) if categories.strip() else []
    cat_raw = normalize(categories) if categories.strip() and not cat_groups else ""
    has_price_bounds = min_val is not None or max_val is not None

    candidates = []
    chains_errors = {}
    stale_any = False

    for cid in chain_ids:
        items, stale, err = fetch_items(cid, refresh=refresh_val)
        if items is None:
            chains_errors[cid] = err or "нет данных"
            continue
        if stale:
            stale_any = True
        chain_name = meta.get(cid, {}).get("name", cid)

        for it in items:
            if cat_groups:
                if category_to_group(it, cid) not in cat_groups:
                    continue
            elif cat_raw:
                if cat_raw not in normalize(it.get("category", "")):
                    continue
            price = it.get("price_rub")
            if has_price_bounds:
                if price is None:
                    continue
                if min_val is not None and price < min_val:
                    continue
                if max_val is not None and price > max_val:
                    continue
            if in_stock_val and it.get("in_stock") is False:
                continue
            s = score_match(query, it.get("name", ""), it.get("category", ""))
            if s <= 0:
                continue
            candidates.append(
                {
                    "chain_id": cid,
                    "chain_name": chain_name,
                    "name": it.get("name", ""),
                    "price_rub": price,
                    "weight_g": it.get("weight_g"),
                    "category": it.get("category", ""),
                    "group": category_to_group(it, cid),
                    "in_stock": it.get("in_stock"),
                    "score": s,
                }
            )

    if sort_val == "price_asc":
        candidates.sort(
            key=lambda x: (
                x["price_rub"] is None,
                x["price_rub"] if x["price_rub"] is not None else 0,
                x["chain_id"],
                x["name"],
            )
        )
    elif sort_val == "price_desc":
        candidates.sort(
            key=lambda x: (
                x["price_rub"] is None,
                -(x["price_rub"] if x["price_rub"] is not None else 0),
                x["chain_id"],
                x["name"],
            )
        )
    else:
        candidates.sort(key=lambda x: (-x["score"], x["chain_id"], x["name"]))

    total = len(candidates)
    results = candidates[:limit_val]

    return json.dumps(
        {
            "query": query,
            "stores_searched": chain_ids,
            "sort": sort_val,
            "limit": limit_val,
            "total": total,
            "results": results,
            "chains_errors": chains_errors,
            "stale": stale_any,
        },
        ensure_ascii=False,
        indent=2,
    )
