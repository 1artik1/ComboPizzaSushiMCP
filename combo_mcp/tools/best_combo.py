# -*- coding: utf-8 -*-
"""best_combo.py — best_combo(chain_id, budget, persons, variations, refresh): N комбо.

Порядок вариаций: Оптимум → Без повторов → Макс. вес → доп. стратегии.
Во всех вариациях — ровно persons напитков (по 1 на персону).
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
from combo_mcp.promos import apply_promos, per_item_discounts
from combo_mcp.params import to_bool, to_int


def best_combo(chain_id, budget, persons=1, variations=3, refresh=False,
               categories="", promos=""):
    """Лучшие варианты комбо для сети при заданном бюджете."""
    try:
        budget = to_int(budget, "budget", minimum=1)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        persons = to_int(persons, "persons", minimum=1)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        variations = to_int(variations, "variations", minimum=1)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        refresh = to_bool(refresh)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    # Валидация promos
    if promos:
        promos = promos.strip().lower()
        if promos not in ("order", "pickup", "all"):
            return json.dumps(
                {"error": "promos должен быть одним из: order, pickup, all"},
                ensure_ascii=False,
            )

    ids = [c["id"] for c in get_chain_meta()]
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'. Доступные: {', '.join(ids)}"}, ensure_ascii=False)

    # Load items
    items, stale, load_error = fetch_items(chain_id, refresh)
    if items is None:
        return json.dumps({"error": f"Нет позиций в кэше и парсинг не удался: {load_error}"}, ensure_ascii=False)

    # Apply reference book for items without weight
    items, estimated_count = apply_estimated_weights(items, chain_id)

    # Все группы сети (до фильтра категорий — для сообщения об ошибке)
    all_groups = sorted(set(category_to_group(it, chain_id) for it in items))

    # Apply category filter if specified
    selected_groups = resolve_categories(categories)
    if selected_groups:
        items = _filter_by_categories(items, chain_id, selected_groups)

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
        # Собираем доступные группы сети
        avail_groups = all_groups
        return json.dumps({
            "chain_id": chain_id,
            "budget": budget,
            "persons": persons,
            "total_items_parsed": len(items),
            "items_with_weight": 0,
            "items_estimated_from_reference": estimated_count,
            "items_without_weight_excluded": no_weight_count,
            "categories": selected_groups,
            "error": (
                f"В меню сети нет позиций категорий: "
                f"{', '.join(selected_groups)}. "
                f"Доступные группы: {', '.join(avail_groups)}"
            ),
        }, ensure_ascii=False, indent=2)

    # Add taste + group
    for p in valid_items:
        p["_taste"] = count_ingredients(p.get("description", ""))
        p["_orig_name"] = p.get("name", "")
        p["_local_name"] = localize(chain_id, p.get("name", ""))
        p["_size_label"] = item_size_label(p)
        p["_group"] = category_to_group(p, chain_id)

    # Calculate combos
    try:
        lines, seed = calculate_combos(valid_items, budget, persons=persons, variations=variations)
    except Exception as e:
        return json.dumps({"error": f"Ошибка расчёта: {e}"}, ensure_ascii=False)

    variants = [_build_combo_line(line, valid_items) for line in lines]

    # Применяем промо: per-item скидки встраиваем в цены ДО расчёта (честный
    # оптимум по фактическим ценам), order/pickup-правила — постобработкой.
    if promos:
        by_idx, per_item_rules = per_item_discounts(chain_id, valid_items, promos)
        if by_idx:
            for idx, disc in by_idx.items():
                it = valid_items[idx]
                it["_base_price"] = it["price_rub"]
                it["_promo_discount"] = disc
                it["price_rub"] = max(it["price_rub"] - disc, 1)
            try:
                lines, seed = calculate_combos(valid_items, budget, persons=persons,
                                               variations=variations)
            except Exception as e:
                return json.dumps({"error": f"Ошибка расчёта: {e}"}, ensure_ascii=False)
            variants = [_build_combo_line(line, valid_items) for line in lines]

        promos_applied = []
        first_promos = None
        for combo in variants:
            items_list = combo.get("items_list")
            if not items_list:
                continue
            base_total = int(sum(
                (x.get("base_price_rub") if x.get("base_price_rub") is not None
                 else x.get("price_rub") or 0) * x.get("count", 1)
                for x in items_list))
            groups = [x.get("group", "") for x in items_list]
            pr = apply_promos(chain_id, combo["price_rub"], promos, groups)
            combo["price_rub"] = base_total
            combo["promo_price"] = pr["promo_price"]
            combo["promo_saved"] = base_total - pr["promo_price"]
            if first_promos is None:
                first_promos = pr["promos"]
        result_promos_applied = (per_item_rules + (first_promos or [])) if variants else []
    else:
        result_promos_applied = []

    result = {
        "chain_id": chain_id,
        "budget": budget,
        "persons": persons,
        "variations_requested": variations,
        "variations_returned": len(variants),
        "seed": seed,
        "stale": stale,
        "stale_error": load_error if stale else None,
        "total_items_parsed": len(items),
        "items_with_weight": len(valid_items),
        "items_estimated_from_reference": estimated_count,
        "items_without_weight_excluded": no_weight_count,
        "categories": selected_groups,
        "weight_sources": dict(Counter(it.get("weight_source", "none") for it in items)),
        "combos": variants,
        "promos_mode": promos,
        "promos_applied": result_promos_applied,
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
            "items_list": build_items_list(items_str, valid_items),
        }
    except (ValueError, IndexError):
        return {"line": line, "weight_g": 0, "price_rub": 0, "price_per_100g": 0.0, "items": "", "items_list": []}


def _filter_by_categories(items, chain_id, selected_groups):
    """Вернуть только позиции, попавшие в выбранные группы категорий."""
    result = []
    for it in items:
        grp = category_to_group(it, chain_id)
        if grp in selected_groups:
            result.append(it)
    return result
