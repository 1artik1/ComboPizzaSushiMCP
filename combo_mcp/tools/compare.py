# -*- coding: utf-8 -*-
"""compare.py — compare(budget, persons): все сети по лучшему варианту.

Как best_combo: справочник весов, persons напитков в комбо, русские названия.
"""

import json
from collections import Counter
from combo_mcp.engines.dp import calculate_combos
from combo_mcp.engines.taste import count_ingredients
from combo_mcp.config import get_chain_meta
from combo_mcp.shared import fetch_items, build_items_list
from combo_mcp.weights import apply_estimated_weights
from combo_mcp.names import localize, item_size_label
from combo_mcp.categories import category_to_group, resolve_categories
from combo_mcp.params import to_int


def compare(budget, persons=1, categories=""):
    """Сравнить все доступные сети по лучшему комбо (persons — сколько персон)."""
    try:
        budget = to_int(budget, "budget", minimum=1)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        persons = to_int(persons, "persons", minimum=1)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    meta = get_chain_meta()
    comparisons = []

    for c in meta:
        cid = c["id"]
        try:
            items, stale, load_error = fetch_items(cid)
            if items is None:
                comparisons.append({
                    "chain_id": cid,
                    "name": c["name"],
                    "available": False,
                    "error": f"Не удалось загрузить: {load_error}",
                })
                continue

            # Apply reference book for items without weight
            items, estimated_count = apply_estimated_weights(items, cid)

            # Apply category filter if specified
            selected_groups = resolve_categories(categories)
            if selected_groups:
                items = [
                    it for it in items
                    if category_to_group(it, cid) in selected_groups
                ]

            no_weight = 0
            valid_items = []
            for it in items:
                w = it.get("weight_g")
                if w is not None and w > 0:
                    p_item = dict(it)
                    p_item["_taste"] = count_ingredients(p_item.get("description", ""))
                    p_item["_orig_name"] = p_item.get("name", "")
                    p_item["_local_name"] = localize(cid, p_item.get("name", ""))
                    p_item["_size_label"] = item_size_label(p_item)
                    valid_items.append(p_item)
                else:
                    no_weight += 1
            no_excluded = no_weight

            # Если ни одной позиции не осталось — пропускаем сеть
            if not valid_items:
                if selected_groups:
                    continue
                comparisons.append({
                    "chain_id": cid,
                    "name": c["name"],
                    "available": False,
                    "error": f"Нет позиций с весом ({no_excluded} без веса пропущено)",
                })
                continue

            # Best combo (optimum, persons drinks inside)
            lines, _ = calculate_combos(valid_items, budget, persons=persons, variations=1)
            if not lines:
                comparisons.append({
                    "chain_id": cid,
                    "name": c["name"],
                    "available": False,
                    "error": "Нет комбо в бюджете",
                })
                continue
            weight, price, items_str = _parse_line(lines[0])

            item_list = build_items_list(items_str, valid_items)
            price_per_100 = price / weight * 100 if weight > 0 else 0
            comparisons.append({
                "chain_id": cid,
                "name": c["name"],
                "available": True,
                "persons": persons,
                "stale": stale,
                "total_weight_g": weight,
                "total_price_rub": price,
                "price_per_100g": round(price_per_100, 2),
                "num_items": len(item_list),
                "items": item_list,
                "items_estimated_from_reference": estimated_count,
                "items_without_weight_excluded": no_excluded,
                "categories": selected_groups,
                "weight_sources": dict(Counter(it.get("weight_source", "none") for it in items)),
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

    # Если все сети отсеяны фильтрами — ошибка
    if not comparisons:
        return json.dumps({
            "error": "Ни одна сеть не имеет позиций выбранных категорий"
        }, ensure_ascii=False, indent=2)

    return json.dumps(comparisons, ensure_ascii=False, indent=2)


def _parse_line(line):
    """'3100 g | 2500 rub | 80.6 rub/100g | items' -> (weight, price, items_str)."""
    parts = line.split(" | ")
    weight = int(parts[0].split()[0])
    price = int(parts[1].split()[0])
    return weight, price, parts[3]