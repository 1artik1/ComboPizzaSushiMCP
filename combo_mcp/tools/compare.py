# -*- coding: utf-8 -*-
"""compare.py — compare(budget, persons): все сети по лучшему варианту.

Как best_combo: справочник весов, persons напитков в комбо, русские названия.
"""

import json
from collections import Counter
from combo_mcp.engines.dp import calculate_combos
from combo_mcp.engines.taste import count_ingredients
from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable
from combo_mcp.weights import apply_estimated_weights
from combo_mcp.names import localize, item_size_label


def compare(budget, persons=1):
    """Сравнить все доступные сети по лучшему комбо (persons — сколько персон)."""
    try:
        budget = int(budget)
    except (TypeError, ValueError):
        return json.dumps({"error": "budget должен быть целым числом > 0"}, ensure_ascii=False)
    if budget <= 0:
        return json.dumps({"error": "budget должен быть > 0"}, ensure_ascii=False)

    try:
        persons = int(persons)
    except (TypeError, ValueError):
        return json.dumps({"error": "persons должен быть целым числом >= 1"}, ensure_ascii=False)
    if persons < 1:
        return json.dumps({"error": "persons должен быть >= 1"}, ensure_ascii=False)

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

            # Apply reference book for items without weight
            items, estimated_count = apply_estimated_weights(items, cid)

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

            if not valid_items:
                comparisons.append({
                    "chain_id": cid,
                    "name": c["name"],
                    "available": False,
                    "error": f"Нет позиций с весом ({no_excluded} без веса пропущено)",
                })
                continue

            # Best combo (optimum, persons drinks inside)
            lines = calculate_combos(valid_items, budget, persons=persons, variations=1)
            if not lines:
                comparisons.append({
                    "chain_id": cid,
                    "name": c["name"],
                    "available": False,
                    "error": "Нет комбо в бюджете",
                })
                continue
            weight, price, items_str = _parse_line(lines[0])

            item_list = _build_item_list(items_str, valid_items)
            price_per_100 = price / weight * 100 if weight > 0 else 0
            comparisons.append({
                "chain_id": cid,
                "name": c["name"],
                "available": True,
                "persons": persons,
                "total_weight_g": weight,
                "total_price_rub": price,
                "price_per_100g": round(price_per_100, 2),
                "num_items": len(item_list),
                "items": item_list,
                "items_estimated_from_reference": estimated_count,
                "items_without_weight_excluded": no_excluded,
                "weight_sources": dict(Counter(it.get("weight_source", "none") for it in items)),
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


def _parse_line(line):
    """'3100 g | 2500 rub | 80.6 rub/100g | items' -> (weight, price, items_str)."""
    parts = line.split(" | ")
    weight = int(parts[0].split()[0])
    price = int(parts[1].split()[0])
    return weight, price, parts[3]


def _strip_size_suffix(name):
    """'Имя (500 г)' -> 'Имя' (отрезаем подпись размера)."""
    import re
    return re.sub(r"\s*\([^()]*\)\s*$", "", name)


def _build_item_list(items_str, valid_items):
    """'Имя (500 г) x2, Имя x1' -> [{name, count, price, weight}, ...]."""
    import re

    by_name = {}
    for it in valid_items:
        by_name.setdefault(it["_local_name"], []).append(it)

    item_list = []
    for chunk in _split_items_str(items_str):
        m = re.match(r"^(.*?)\s*x(\d+)$", chunk)
        name = _strip_size_suffix(m.group(1).strip()) if m else _strip_size_suffix(chunk)
        cnt = int(m.group(2)) if m else 1
        pool = by_name.get(name)
        it = pool.pop(0) if pool else None
        item_list.append({
            "name": name,
            "count": cnt,
            "price": it["price_rub"] if it else None,
            "weight": it["weight_g"] if it else None,
        })
    return item_list


def _split_items_str(items_str):
    """Разбить по запятым вне скобок ('НАГГЕТСЫ (9 шт, 20 г/шт)' — одна часть)."""
    parts, depth, cur = [], 0, ""
    for ch in items_str:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            if cur.strip():
                parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


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