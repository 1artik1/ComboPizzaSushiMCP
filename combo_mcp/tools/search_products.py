# -*- coding: utf-8 -*-
"""search_products.py — search_products(chain_id, query, limit=20, refresh=False).

Поиск товаров по названию в любой сети.
- Для серверных сетей (magnit/pyaterochka) — серверный поиск API.
- Для остальных — локальный регистронезависимый поиск по подстроке в name.
"""

import json

from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.shared import fetch_items
from combo_mcp.params import to_int, to_bool
from combo_mcp.chains.base import ChainUnavailable


def search_products(chain_id, query, limit="20", refresh="false"):
    """Поиск товаров по названию в любой сети."""
    if not chain_id:
        return json.dumps({"error": "Не указан chain_id"}, ensure_ascii=False)

    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        available = ", ".join(sorted(ids))
        return json.dumps(
            {
                "error": f"Неизвестная сеть '{chain_id}'. Доступны: {available}",
            },
            ensure_ascii=False,
        )

    if not query or not query.strip():
        return json.dumps(
            {"error": "Не указан query (поисковый запрос)"}, ensure_ascii=False
        )

    try:
        limit_val = to_int(limit, "limit", minimum=1)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        refresh_val = to_bool(refresh)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    cls = get_chain_class(chain_id)
    if cls is None:
        return json.dumps(
            {"error": f"Парсер для '{chain_id}' не найден"}, ensure_ascii=False
        )

    meta = {c["id"]: c for c in get_chain_meta()}
    chain_name = meta.get(chain_id, {}).get("name", chain_id)

    # Проверяем, есть ли рабочий серверный поиск
    if getattr(cls, "has_server_search", False):
        # Серверный путь: magnit/pyaterochka
        try:
            results = cls().search(query.strip(), limit=limit_val)
        except ChainUnavailable as e:
            return json.dumps(
                {
                    "chain_id": chain_id,
                    "chain_name": chain_name,
                    "query": query,
                    "source": "server",
                    "error": str(e),
                },
                ensure_ascii=False,
                indent=2,
            )

        # Сортировка по price_rub asc
        results.sort(key=lambda x: x.get("price_rub") or float("inf"))
        total = len(results)
        results = results[:limit_val]

        return json.dumps(
            {
                "chain_id": chain_id,
                "chain_name": chain_name,
                "query": query,
                "source": "server",
                "total": total,
                "limit": limit_val,
                "results": [
                    {
                        "name": r.get("name", ""),
                        "price_rub": r.get("price_rub"),
                        "weight_g": r.get("weight_g"),
                        "category": r.get("category", ""),
                        "in_stock": r.get("in_stock"),
                    }
                    for r in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    # Меню-путь: fetch + локальный поиск
    items, stale, err = fetch_items(chain_id, refresh=refresh_val)
    if items is None:
        return json.dumps(
            {
                "chain_id": chain_id,
                "chain_name": chain_name,
                "query": query,
                "source": "menu",
                "error": f"Не удалось загрузить меню: {err or 'нет данных'}",
            },
            ensure_ascii=False,
            indent=2,
        )

    query_lower = query.strip().lower()
    found = []
    for it in items:
        name = it.get("name", "")
        if query_lower in name.lower():
            found.append(it)

    # Сортировка по price_rub asc
    found.sort(key=lambda x: x.get("price_rub") or float("inf"))
    total = len(found)
    found = found[:limit_val]

    return json.dumps(
        {
            "chain_id": chain_id,
            "chain_name": chain_name,
            "query": query,
            "source": "menu",
            "total": total,
            "limit": limit_val,
            "results": [
                {
                    "name": r.get("name", ""),
                    "price_rub": r.get("price_rub"),
                    "weight_g": r.get("weight_g"),
                    "category": r.get("category", ""),
                    "in_stock": r.get("in_stock"),
                }
                for r in found
            ],
            "stale": stale,
        },
        ensure_ascii=False,
        indent=2,
    )
