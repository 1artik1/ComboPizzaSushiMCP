# -*- coding: utf-8 -*-
"""best_combo.py — best_combo(chain_id, budget, persons, variations, refresh): N комбо.

Порядок вариаций: Оптимум → Без повторов → Макс. вес → доп. стратегии.
Во всех вариациях — ровно persons напитков (по 1 на персону).
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


def best_combo(chain_id, budget, persons=1, variations=3, refresh=False):
    """Лучшие варианты комбо для сети при заданном бюджете."""
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

    try:
        variations = int(variations)
    except (TypeError, ValueError):
        return json.dumps({"error": "variations должен быть целым числом >= 1"}, ensure_ascii=False)
    if variations < 1:
        return json.dumps({"error": "variations должен быть >= 1"}, ensure_ascii=False)

    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    # Load items
    items = _load_items(chain_id, refresh)
    if items is None:
        return json.dumps({"error": "Нет позиций в кэше и парсинг не удался"}, ensure_ascii=False)

    # Apply reference book for items without weight
    items, estimated_count = apply_estimated_weights(items, chain_id)

    # Filter: must have valid weight_g > 0
    no_weight_count = 0
    valid_items = []
    for it in items:
        w = it.get("weight_g")
        if w is not None and w > 0:
            valid_items.append(it)
        else:
            no_weight_count += 1

    if not valid_items:
        return json.dumps({
            "chain_id": chain_id,
            "budget": budget,
            "persons": persons,
            "total_items_parsed": len(items),
            "items_with_weight": 0,
            "items_estimated_from_reference": estimated_count,
            "items_without_weight_excluded": no_weight_count,
            "error": f"Нет позиций с весом для {chain_id} ({len(items)} всего, {no_weight_count} без веса).",
        }, ensure_ascii=False, indent=2)

    # Add taste
    for p in valid_items:
        p["_taste"] = count_ingredients(p.get("description", ""))
        p["_orig_name"] = p.get("name", "")
        p["_local_name"] = localize(chain_id, p.get("name", ""))
        p["_size_label"] = item_size_label(p)

    # Calculate combos
    try:
        lines, seed = calculate_combos(valid_items, budget, persons=persons, variations=variations)
    except Exception as e:
        return json.dumps({"error": f"Ошибка расчёта: {e}"}, ensure_ascii=False)

    variants = [_build_combo_line(line, valid_items) for line in lines]

    result = {
        "chain_id": chain_id,
        "budget": budget,
        "persons": persons,
        "variations_requested": variations,
        "variations_returned": len(variants),
        "seed": seed,
        "total_items_parsed": len(items),
        "items_with_weight": len(valid_items),
        "items_estimated_from_reference": estimated_count,
        "items_without_weight_excluded": no_weight_count,
        "weight_sources": dict(Counter(it.get("weight_source", "none") for it in items)),
        "combos": variants,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _build_combo_line(line, valid_items):
    """Разобрать строку комбо в структуру + список позиций с весом/ценой."""
    parts = line.split(" | ")
    if len(parts) < 4:
        return {"line": line, "weight_g": 0, "price_rub": 0, "price_per_100g": 0.0, "items": "", "items_list": []}
    try:
        weight_str = parts[0].split()[0]
        price_str = parts[1].split()[0]
        per100 = parts[2].split()[0]
        items_str = parts[3]
        return {
            "line": line,
            "weight_g": int(weight_str),
            "price_rub": int(price_str),
            "price_per_100g": float(per100),
            "items": items_str,
            "items_list": _items_list(items_str, valid_items),
        }
    except (ValueError, IndexError):
        return {"line": line, "weight_g": 0, "price_rub": 0, "price_per_100g": 0.0, "items": "", "items_list": []}


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


def _items_list(items_str, valid_items):
    """'Имя (500 г) x2, Имя x1' -> [{name, count, price_rub, weight_g, weight_source}, ...].

    Повторяющиеся имена (одинаковые товары по разным ценам) маппятся по очереди.
    """
    import re

    by_name = {}
    for it in valid_items:
        by_name.setdefault(it["_local_name"], []).append(it)

    out = []
    for chunk in _split_items_str(items_str):
        m = re.match(r"^(.*?)\s*x(\d+)$", chunk)
        name = re.sub(r"\s*\([^()]*\)\s*$", "", m.group(1).strip()) if m else chunk
        cnt = int(m.group(2)) if m else 1
        pool = by_name.get(name)
        it = pool.pop(0) if pool else None
        out.append({
            "name": name,
            "count": cnt,
            "price_rub": it["price_rub"] if it else None,
            "weight_g": it["weight_g"] if it else None,
            "weight_source": it.get("weight_source") if it else None,
        })
    return out


def _load_items(chain_id, refresh=False):
    """Load items from cache or fresh parse."""
    if not refresh:
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
