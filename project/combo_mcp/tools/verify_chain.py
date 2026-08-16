# -*- coding: utf-8 -*-
"""verify_chain.py — валидация сети: кол-во позиций, с весом/без, «от»-цены, дубликаты, аномалии."""

import json
from collections import Counter
from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable


def verify_chain(chain_id):
    """Валидация сети."""
    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    # Load items
    items = _load_items(chain_id)
    if items is None:
        return json.dumps({"error": "Не удалось загрузить позиции"}, ensure_ascii=False)

    issues = []
    with_weight = sum(1 for it in items if it.get("weight_g") and it["weight_g"] > 0)
    without_weight = len(items) - with_weight

    # "from" prices
    from_prices = [it for it in items if it.get("is_from_price", False)]

    # Duplicate names
    name_counts = Counter(it["name"] for it in items)
    duplicates = {name: cnt for name, cnt in name_counts.items() if cnt > 1}

    # Weight anomalies
    weight_anomalies = [
        it for it in items
        if it.get("weight_g") and (it["weight_g"] < 50 or it["weight_g"] > 5000)
    ]

    # in_stock = False
    out_of_stock = [it for it in items if not it.get("in_stock", True)]

    # Build result
    result = {
        "chain_id": chain_id,
        "total_items": len(items),
        "with_weight": with_weight,
        "without_weight": without_weight,
        "from_prices": len(from_prices),
        "duplicates": duplicates,
        "weight_anomalies": len(weight_anomalies),
        "out_of_stock": len(out_of_stock),
    }

    if weight_anomalies:
        issues.append(f"Аномалии веса: {len(weight_anomalies)} позиций (<50г или >5000г)")
    if duplicates:
        issues.append(f"Дубликаты имён: {duplicates}")
    if out_of_stock:
        issues.append(f"Нет в наличии: {len(out_of_stock)} позиций")

    result["issues"] = issues
    result["status"] = "OK" if not issues else "PROBLEMS"

    return json.dumps(result, ensure_ascii=False, indent=2)


def _load_items(chain_id):
    """Load items from cache or fresh parse."""
    cache_data = load_cache(chain_id)
    if cache_data:
        return cache_data.get("items", [])

    try:
        chain_cls = get_chain_class(chain_id)
        if chain_cls is None:
            return None
        instance = chain_cls()
        items = instance.parse()
        save_cache(chain_id, items)
        return items
    except ChainUnavailable:
        return None
    except Exception:
        return None
