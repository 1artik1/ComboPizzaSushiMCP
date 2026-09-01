# -*- coding: utf-8 -*-
"""diff_menu.py — diff_menu(chain_id): сравнение items vs prev_items."""

import json
from combo_mcp.cache import load_cache
from combo_mcp.config import get_chain_meta
from combo_mcp.chains.base import get_chain_class, ChainUnavailable


def diff_menu(chain_id):
    """Сравнение меню с предыдущей версией."""
    chain_id = (chain_id or "").strip()
    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    cache_data = load_cache(chain_id)
    if cache_data is None:
        return json.dumps({"error": "Нет кэша для сравнения. Сначала распарсите меню."}, ensure_ascii=False)

    current = cache_data.get("items", [])
    prev = cache_data.get("prev_items", [])

    if not prev:
        return json.dumps({"error": "Нет prev_items в кэше. Сохраните кэш после парсинга."}, ensure_ascii=False)

    # Build lookup by name
    cur_map = {it["name"]: it for it in current}
    prev_map = {it["name"]: it for it in prev}

    cur_names = set(cur_map.keys())
    prev_names = set(prev_map.keys())

    added = list(cur_names - prev_names)
    removed = list(prev_names - cur_names)
    changed = []

    for name in cur_names & prev_names:
        cur_it = cur_map[name]
        prev_it = prev_map[name]
        changes = {}
        if cur_it.get("price_rub") != prev_it.get("price_rub"):
            changes["price"] = {"from": prev_it["price_rub"], "to": cur_it["price_rub"]}
        if cur_it.get("weight_g") != prev_it.get("weight_g"):
            changes["weight"] = {"from": prev_it["weight_g"], "to": cur_it["weight_g"]}
        if changes:
            changed.append({"name": name, "changes": changes})

    result = {
        "chain_id": chain_id,
        "current_count": len(current),
        "prev_count": len(prev),
        "added": added,
        "removed": removed,
        "changed": changed,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)
