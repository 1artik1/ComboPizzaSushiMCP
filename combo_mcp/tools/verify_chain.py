# -*- coding: utf-8 -*-
"""verify_chain.py — валидация сети: кол-во позиций, с весом/без, «от»-цены, дубликаты, аномалии."""

import json
import re
from collections import Counter
from combo_mcp.config import get_chain_meta
from combo_mcp.shared import fetch_items
from combo_mcp.weights import apply_estimated_weights


def verify_chain(chain_id):
    """Валидация сети."""
    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    # Load items
    items, stale, load_error = fetch_items(chain_id)
    if items is None:
        return json.dumps({"error": f"Не удалось загрузить позиции: {load_error}"}, ensure_ascii=False)

    issues = []
    items, estimated_count = apply_estimated_weights(items, chain_id)
    weight_sources = dict(Counter(it.get("weight_source", "none") for it in items))
    with_weight = sum(1 for it in items if it.get("weight_g") and it["weight_g"] > 0)
    without_weight = len(items) - with_weight

    # "from" prices
    from_prices = [it for it in items if it.get("is_from_price", False)]

    # Duplicate names: дубликат = то же имя, цена, вес и категория
    # (разные размеры одной пиццы с разными ценами — легальные позиции)
    norm = re.compile(r"\s+")
    dup_key = {}
    duplicates = {}
    for it in items:
        key = (
            norm.sub(" ", it.get("name", "")).strip().lower(),
            it.get("price_rub"),
            it.get("weight_g"),
            it.get("category", ""),
        )
        dup_key.setdefault(key, []).append(it["name"])
    for key, names in dup_key.items():
        if len(names) > 1:
            duplicates[key[0]] = len(names)

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
        "items_estimated_from_reference": estimated_count,
        "weight_sources": weight_sources,
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
    result["stale"] = stale
    if stale and load_error:
        result["stale_error"] = load_error

    return json.dumps(result, ensure_ascii=False, indent=2)
