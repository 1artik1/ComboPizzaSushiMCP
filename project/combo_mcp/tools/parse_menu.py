# -*- coding: utf-8 -*-
"""parse_menu.py — parse_menu(chain_id, category, min_weight, sort_by, limit, refresh)."""

import json
from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable


def parse_menu(chain_id, category=None, min_weight=None, sort_by=None, limit=None, refresh=False):
    """Распарсить меню конкретной сети."""
    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    # Try cache
    if not refresh:
        cache_data = load_cache(chain_id)
        if cache_data:
            items = cache_data.get("items", [])
            return _filter_sort(items, category, min_weight, sort_by, limit)

    # Parse fresh
    try:
        chain_cls = get_chain_class(chain_id)
        if chain_cls is None:
            raise ChainUnavailable(f"Не найден парсер для {chain_id}")
        instance = chain_cls()
        items = instance.parse()
        save_cache(chain_id, items)
    except ChainUnavailable as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    return _filter_sort(items, category, min_weight, sort_by, limit)


def _filter_sort(items, category, min_weight, sort_by, limit):
    """Filter and sort items."""
    result = []
    for it in items:
        if category and it.get("category") != category:
            continue
        if min_weight and it.get("weight_g") is not None and it["weight_g"] < min_weight:
            continue
        result.append(dict(it))

    if sort_by == "price_per_100g":
        result.sort(key=lambda x: x["price_rub"] / x["weight_g"] if x.get("weight_g") and x["weight_g"] > 0 else float('inf'))
    elif sort_by == "price":
        result.sort(key=lambda x: x["price_rub"])
    elif sort_by == "weight":
        result.sort(key=lambda x: x["weight_g"] if x.get("weight_g") else 0, reverse=True)

    if limit:
        result = result[:limit]

    return json.dumps(result, ensure_ascii=False, indent=2)
