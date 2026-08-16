# -*- coding: utf-8 -*-
"""best_combo.py — best_combo(chain_id, budget, refresh): 3 комбо."""

import json
from combo_mcp.engines.dp import calculate_combos
from combo_mcp.engines.taste import count_ingredients
from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable


def best_combo(chain_id, budget, refresh=False):
    """Лучшие 3 варианта комбо для сети при заданном бюджете."""
    try:
        budget = int(budget)
    except (TypeError, ValueError):
        return json.dumps({"error": "budget должен быть целым числом > 0"}, ensure_ascii=False)
    if budget <= 0:
        return json.dumps({"error": "budget должен быть > 0"}, ensure_ascii=False)

    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    # Load items
    items = _load_items(chain_id, refresh)
    if items is None:
        return json.dumps({"error": "Нет позиций в кэше и парсинг не удался"}, ensure_ascii=False)

    # Filter: must have valid weight_g > 0
    no_weight_count = 0
    valid_items = []
    for it in items:
        w = it.get("weight_g")
        if w is not None and w > 0:
            valid_items.append(dict(it))
        else:
            no_weight_count += 1

    if not valid_items:
        return json.dumps({
            "chain_id": chain_id,
            "budget": budget,
            "total_items_parsed": len(items),
            "items_with_weight": 0,
            "items_without_weight_excluded": no_weight_count,
            "error": f"Нет позиций с весом для {chain_id} ({len(items)} всего, {no_weight_count} без веса).",
        }, ensure_ascii=False, indent=2)

    # Add taste
    for p in valid_items:
        p["_taste"] = count_ingredients(p.get("description", ""))

    # Calculate combos
    try:
        line1, line2, line3 = calculate_combos(valid_items, budget)
    except Exception as e:
        return json.dumps({"error": f"Ошибка расчёта: {e}"}, ensure_ascii=False)

    def _build_combo_line(line):
        parts = line.split(" | ")
        if len(parts) < 4:
            return {"line": line, "weight_g": 0, "price_rub": 0, "price_per_100g": 0.0, "items": ""}
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
            }
        except (ValueError, IndexError):
            return {"line": line, "weight_g": 0, "price_rub": 0, "price_per_100g": 0.0, "items": ""}

    result = {
        "chain_id": chain_id,
        "budget": budget,
        "total_items_parsed": len(items),
        "items_with_weight": len(valid_items),
        "items_without_weight_excluded": no_weight_count,
        "combo_max_weight": _build_combo_line(line1),
        "combo_optimum": _build_combo_line(line2),
        "combo_no_duplicates": _build_combo_line(line3),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


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
