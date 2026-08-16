# -*- coding: utf-8 -*-
"""compare.py — compare(budget): все сети по лучшему варианту."""

import json
from collections import Counter
from combo_mcp.engines.dp import solve_max_weight_double
from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable


def compare(budget):
    """Сравнить все доступные сети по лучшему комбо."""
    try:
        budget = int(budget)
    except (TypeError, ValueError):
        return json.dumps({"error": "budget должен быть целым числом > 0"}, ensure_ascii=False)
    if budget <= 0:
        return json.dumps({"error": "budget должен быть > 0"}, ensure_ascii=False)

    meta = get_chain_meta()
    comparisons = []

    for c in meta:
        cid = c["id"]
        try:
            items = _load_items(cid)
            if items is None:
                comparisons.append({
                    "chain_id": cid,
                    "name": c["name"],
                    "available": False,
                    "error": "Не удалось загрузить",
                })
                continue

            no_weight = 0
            no_price = 0
            valid_items = []
            for it in items:
                w = it.get("weight_g")
                p = it.get("price_rub")
                if w is not None and w > 0 and p is not None and p > 0:
                    valid_items.append(dict(it))
                elif w is None or w <= 0:
                    no_weight += 1
                else:
                    no_price += 1
            no_excluded = no_weight + no_price

            if not valid_items:
                comparisons.append({
                    "chain_id": cid,
                    "name": c["name"],
                    "available": False,
                    "error": f"Нет позиций с весом ({no_excluded} без веса/цены пропущено)",
                })
                continue

            # Calculate best combo (max weight)
            indices, total_weight, total_cost = solve_max_weight_double(valid_items, budget)

            # Build item list
            counts = Counter()
            for idx, cnt in indices:
                counts[idx] += cnt
            item_list = []
            for idx, cnt in counts.items():
                it = valid_items[idx]
                item_list.append({
                    "name": it["name"],
                    "count": cnt,
                    "price": it["price_rub"],
                    "weight": it["weight_g"],
                })

            price_per_100 = total_cost / total_weight * 100 if total_weight > 0 else 0
            comparisons.append({
                "chain_id": cid,
                "name": c["name"],
                "available": True,
                "total_weight_g": total_weight,
                "total_price_rub": total_cost,
                "price_per_100g": round(price_per_100, 2),
                "num_items": len(item_list),
                "items": item_list,
                "items_without_weight_excluded": no_excluded,
            })
        except ChainUnavailable as e:
            comparisons.append({
                "chain_id": cid,
                "name": c["name"],
                "available": False,
                "error": str(e),
            })
        except Exception as e:
            comparisons.append({
                "chain_id": cid,
                "name": c["name"],
                "available": False,
                "error": str(e),
            })

    # Sort by price_per_100g (lower is better)
    comparisons.sort(key=lambda x: x.get("price_per_100g", float('inf')))

    return json.dumps(comparisons, ensure_ascii=False, indent=2)


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
