# -*- coding: utf-8 -*-
"""store_categories.py — дерево категорий только магазинов (kind=store).

store_categories(store) возвращает серверное дерево категорий магазина
через parser.get_categories(). Рестораны здесь не участвуют.

Для магазинов без серверных категорий (или restaurant) — ошибка.
Для Пятёрочки (отключена, анти-бот) — ошибка с пояснением.
"""

import json

from combo_mcp.config import get_chain_meta, get_chain_class, get_store_chain_ids, get_chain_kind
from combo_mcp.chains.base import ChainUnavailable


def _err(msg):
    return json.dumps({"error": msg}, ensure_ascii=False)


def store_categories(store=""):
    """Дерево категорий одного магазина или всех включённых магазинов."""
    meta = {c["id"]: c for c in get_chain_meta()}
    store_ids = get_store_chain_ids()

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
                f"Для категорий ресторанов используйте parse_menu."
            )
        targets = [p for p in parts if p in store_ids]

    entries = []
    for cid in targets:
        cls = get_chain_class(cid)
        chain_name = meta.get(cid, {}).get("name", cid)
        if cls is None or not getattr(cls, "has_server_search", False):
            entries.append({
                "store_id": cid,
                "store_name": chain_name,
                "error": "у магазина нет серверного дерева категорий",
            })
            continue
        try:
            categories = cls().get_categories()
        except ChainUnavailable as e:
            entries.append({
                "store_id": cid,
                "store_name": chain_name,
                "error": str(e),
            })
            continue
        except Exception as e:
            entries.append({
                "store_id": cid,
                "store_name": chain_name,
                "error": f"get_categories error: {e}",
            })
            continue
        total = len(categories) if isinstance(categories, list) else 0
        entries.append({
            "store_id": cid,
            "store_name": chain_name,
            "categories": categories,
            "total": total,
        })

    return json.dumps(
        {
            "stores_requested": targets,
            "results": entries,
        },
        ensure_ascii=False,
        indent=2,
    )