# -*- coding: utf-8 -*-
"""list_categories.py — list_categories(chain_id, refresh=False).

Все категории товаров сети: серверное дерево (magnit/pyaterochka)
или агрегат по меню (остальные сети).
"""

import json

from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.shared import fetch_items
from combo_mcp.params import to_bool
from combo_mcp.chains.base import ChainUnavailable


def list_categories(chain_id, refresh="false"):
    """Все категории товаров сети."""
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

    # Проверяем, есть ли рабочий серверный поиск/категории
    if getattr(cls, "has_server_search", False):
        # Серверный путь: magnit/pyaterochka
        try:
            categories = cls().get_categories()
        except ChainUnavailable as e:
            return json.dumps(
                {
                    "chain_id": chain_id,
                    "chain_name": chain_name,
                    "source": "server",
                    "error": str(e),
                },
                ensure_ascii=False,
                indent=2,
            )

        # total = число ТОП-категорий
        total = len(categories) if isinstance(categories, list) else 0

        return json.dumps(
            {
                "chain_id": chain_id,
                "chain_name": chain_name,
                "source": "server",
                "categories": categories,
                "total": total,
            },
            ensure_ascii=False,
            indent=2,
        )

    # Меню-путь: fetch + агрегация по category
    items, stale, err = fetch_items(chain_id, refresh=refresh_val)
    if items is None:
        return json.dumps(
            {
                "chain_id": chain_id,
                "chain_name": chain_name,
                "source": "menu",
                "error": f"Не удалось загрузить меню: {err or 'нет данных'}",
            },
            ensure_ascii=False,
            indent=2,
        )

    # Агрегация по полю category, пустые пропускаем
    cat_counts = {}
    for it in items:
        cat = it.get("category", "")
        if not cat or not cat.strip():
            continue
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # Сортировка: по count desc, затем по имени asc
    result = [{"category": cat, "count": count} for cat, count in cat_counts.items()]
    result.sort(key=lambda x: (-x["count"], x["category"]))

    return json.dumps(
        {
            "chain_id": chain_id,
            "chain_name": chain_name,
            "source": "menu",
            "categories": result,
            "total": len(result),
            "items_total": len(items),
            "stale": stale,
        },
        ensure_ascii=False,
        indent=2,
    )
