# -*- coding: utf-8 -*-
"""best_combo.py — best_combo(chain_id, budget, variations, refresh): N комбо.

Порядок вариаций: Оптимум → Без повторов → Макс. вес → доп. стратегии.
Во всех вариациях — ровно 1 напиток (TARGET_DRINKS).

Сквозной топ-N: chain_id="" — все сети, "id1, id2" — выбранные сети.
В cross-chain режиме кандидаты сетей (стратегии + добивка топ-позициями
по метрике) сортируются метрикой sort_by и отбирается топ variations.
"""

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from combo_mcp.engines.dp import calculate_combos
from combo_mcp.engines.taste import count_ingredients
from combo_mcp.config import get_chain_meta, get_combo_chain_ids, get_store_chain_ids
from combo_mcp.shared import fetch_items, build_items_list
from combo_mcp.weights import apply_estimated_weights
from combo_mcp.names import localize, item_size_label
from combo_mcp.categories import category_to_group, resolve_categories, ALL_GROUPS
from combo_mcp.promos import apply_promos, per_item_discounts
from combo_mcp.params import to_bool, to_int, MAX_BUDGET, MAX_VARIATIONS

_VALID_SORTS = ("price_per_100g", "weight", "price")


def best_combo(chain_id, budget, variations=3, refresh=False,
               categories="", promos="", sort_by="price_per_100g"):
    """Лучшие варианты комбо при заданном бюджете.

    chain_id: одна сеть — прежнее поведение (mode="single"); пустая строка —
    все сети; список через запятую — только эти сети (cross-chain топ-N).
    """
    try:
        budget = to_int(budget, "budget", minimum=1, maximum=MAX_BUDGET)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    try:
        variations = to_int(variations, "variations", minimum=1,
                            maximum=MAX_VARIATIONS)
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

    # sort_by валидируем всегда, используется только в cross-chain режиме
    sort_by = (sort_by or "price_per_100g").strip().lower()
    if not sort_by:
        sort_by = "price_per_100g"
    if sort_by not in _VALID_SORTS:
        return json.dumps({
            "error": f"sort_by должен быть одним из: {', '.join(_VALID_SORTS)}"
        }, ensure_ascii=False)

    # Нераспознанные категории — явная ошибка (не молча без фильтра)
    categories = (categories or "").strip()
    if categories:
        groups = resolve_categories(categories)
        if not groups:
            return json.dumps({
                "error": f"Неизвестные категории: '{categories}'. "
                         f"Доступные группы: {', '.join(ALL_GROUPS)}"
            }, ensure_ascii=False)

    # Разбор chain_id: "" → все, "a, b" → список
    targets = _resolve_chain_ids(chain_id)
    if isinstance(targets, str):
        return targets
    if len(targets) > 1 or (chain_id or "").strip() == "":
        return _cross_chain(chain_id, targets, budget, variations,
                            refresh, categories, promos, sort_by)

    # ---- single-chain: прежнее поведение ----
    chain_id = targets[0]
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
        lines, seed = calculate_combos(valid_items, budget, variations=variations)
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
                lines, seed = calculate_combos(valid_items, budget,
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


# ---------------------------------------------------------------- блок 2
# Сквозной топ-N: кандидаты сетей (стратегии + добивка топ-позициями),
# сортировка метрикой, отбор топ variations.

def _resolve_chain_ids(chain_id):
    """Разобрать chain_id на список id сетей.

    "" / пробелы → включённые рестораны (kind=combo); "a, b" → список (trim).
    Магазины (kind=store) в комбо не участвуют — при явном запросе возвращают
    ошибку с указанием store-tools. Неизвестный id → строка-ошибка.
    """
    meta = get_chain_meta()
    ids = [c["id"] for c in meta]
    store_ids = get_store_chain_ids()
    raw = (chain_id or "").strip()
    if not raw:
        return list(get_combo_chain_ids())
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    unknown = [p for p in parts if p not in ids]
    if unknown:
        return json.dumps({
            "error": f"Неизвестная сеть '{unknown[0]}'. Доступные: {', '.join(ids)}"
        }, ensure_ascii=False)
    stores = [p for p in parts if p in store_ids]
    if stores:
        return json.dumps({
            "error": f"Магазины не участвуют в комбо: {', '.join(stores)}. "
                     f"Для поиска товаров используйте store_search/store_categories."
        }, ensure_ascii=False)
    return list(dict.fromkeys(parts))


def _combo_metric(combo, sort_by):
    """Значение метрики комбо для сортировки (ключ сортировки — в _sort_combos)."""
    if sort_by == "weight":
        return combo.get("weight_g", 0)
    if sort_by == "price":
        return combo.get("price_rub", 0)
    return combo.get("price_per_100g", 0.0)


def _sort_combos(combos, sort_by):
    """Отсортировать комбо по метрике: price_per_100g/price — меньше лучше,
    weight — больше лучше."""
    if sort_by == "weight":
        combos.sort(key=lambda c: c.get("weight_g", 0), reverse=True)
    elif sort_by == "price":
        combos.sort(key=lambda c: c.get("price_rub", 0))
    else:
        combos.sort(key=lambda c: c.get("price_per_100g", 0.0))


def _build_single_item_combo(it):
    """Комбо из одной позиции (добивка кандидатов) — те же поля, что у вариаций."""
    w = it.get("weight_g") or 0
    p = it.get("price_rub") or 0
    per100 = p / w * 100 if w > 0 else 0.0
    label = it.get("_size_label", "")
    display = it.get("_local_name") or it.get("name", "")
    name = f"{display} ({label}) x1" if label else f"{display} x1"
    line = f"{w} g | {p} rub | {per100:.1f} rub/100g | {name}"
    return {"line": line, "weight_g": w, "price_rub": p,
            "price_per_100g": round(per100, 1), "items": name}


def _pad_candidates(valid_items, budget, need, existing, sort_by):
    """Добить список кандидатов сети топ-позициями по метрике (до variations).

    Случай «10 напитков»: стратегии схлопываются в одно комбо — держим
    отдельные позиции как кандидаты, чтобы сеть участвовала в топ-N.
    """
    seen = {c["items"] for c in existing}
    cand = [it for it in valid_items if (it.get("price_rub") or 0) <= budget]
    if sort_by == "weight":
        cand.sort(key=lambda x: (-(x.get("weight_g") or 0), x.get("price_rub") or 0))
    elif sort_by == "price":
        cand.sort(key=lambda x: (x.get("price_rub") or 0, -(x.get("weight_g") or 0)))
    else:
        cand.sort(key=lambda x: ((x.get("price_rub") or 0) / (x.get("weight_g") or 1)
                                 if (x.get("weight_g") or 0) > 0 else float("inf"),
                                 -(x.get("weight_g") or 0)))

    out = []
    for it in cand:
        if len(out) >= need:
            break
        combo = _build_single_item_combo(it)
        if combo["items"] in seen:
            continue
        seen.add(combo["items"])
        out.append(combo)
    return out


def _chain_candidates(chain_id, budget, variations, refresh, categories, promos, sort_by):
    """Кандидаты одной сети для cross-chain: комбо (стратегии) + добивка.

    Возвращает dict {chain_id, name, combos: [...], error: str|None}.
    """
    meta_by = {c["id"]: c for c in get_chain_meta()}
    meta = meta_by.get(chain_id, {})
    result = {"chain_id": chain_id, "name": meta.get("name", chain_id),
              "combos": [], "error": None}

    items, stale, load_error = fetch_items(chain_id, refresh)
    if items is None:
        result["error"] = f"Не удалось загрузить: {load_error}"
        return result

    items, _ = apply_estimated_weights(items, chain_id)
    selected_groups = resolve_categories(categories)
    if selected_groups:
        items = _filter_by_categories(items, chain_id, selected_groups)

    valid_items = []
    for it in items:
        w = it.get("weight_g")
        if w is not None and w > 0 and (it.get("price_rub") or 0) > 0:
            valid_items.append(it)
    if not valid_items:
        result["error"] = f"Нет позиций выбранных категорий ({', '.join(selected_groups)})" \
            if selected_groups else "Нет позиций с весом"
        return result

    for p in valid_items:
        p["_taste"] = count_ingredients(p.get("description", ""))
        p["_orig_name"] = p.get("name", "")
        p["_local_name"] = localize(chain_id, p.get("name", ""))
        p["_size_label"] = item_size_label(p)

    try:
        lines, _ = calculate_combos(valid_items, budget, variations=variations)
    except Exception as e:
        result["error"] = f"Ошибка расчёта: {e}"
        return result
    if not lines:
        result["error"] = "Нет комбо в бюджете"
        return result

    if promos:
        by_idx, _ = per_item_discounts(chain_id, valid_items, promos)
        if by_idx:
            for idx, disc in by_idx.items():
                it = valid_items[idx]
                it["_base_price"] = it["price_rub"]
                it["_promo_discount"] = disc
                it["price_rub"] = max(it["price_rub"] - disc, 1)
            try:
                lines, _ = calculate_combos(valid_items, budget,
                                            variations=variations)
            except Exception as e:
                result["error"] = f"Ошибка расчёта: {e}"
                return result
            if not lines and by_idx:
                result["error"] = "Нет комбо в бюджете"
                return result

    combos = [_build_combo_line(line, valid_items) for line in lines]
    result["stale"] = stale
    result["stale_error"] = load_error if stale else None

    if promos:
        for combo in combos:
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

    # добивка до variations топ-позициями по метрике
    if len(combos) < variations:
        combos += _pad_candidates(valid_items, budget, variations - len(combos),
                                  combos, sort_by)
    result["combos"] = combos
    return result


def _cross_chain(chain_id, targets, budget, variations, refresh, categories, promos, sort_by):
    """Сквозной топ-N: кандидаты сетей → сортировка метрикой → топ variations."""
    mode = "all" if not (chain_id or "").strip() else "multi"

    def _run(cid):
        return _chain_candidates(cid, budget, variations, refresh, categories,
                                 promos, sort_by)

    if refresh:
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(_run, targets))
    else:
        results = [_run(cid) for cid in targets]

    pool = []
    chains, skipped = [], []
    for r in results:
        if r["error"] or not r["combos"]:
            skipped.append({"chain_id": r["chain_id"], "name": r["name"],
                            "error": r["error"]})
            continue
        chains.append(r["chain_id"])
        for combo in r["combos"]:
            combo["chain_id"] = r["chain_id"]
            combo["name"] = r["name"]
            pool.append(combo)

    _sort_combos(pool, sort_by)
    top = pool[:variations]
    for rank, combo in enumerate(top, start=1):
        combo["rank"] = rank

    if not top:
        return json.dumps({
            "mode": mode,
            "budget": budget,
            "variations_requested": variations,
            "variations_returned": 0,
            "chains": [],
            "skipped_chains": skipped,
            "error": "Ни одна сеть не дала комбо в бюджете",
            "sort_by": sort_by,
        }, ensure_ascii=False, indent=2)

    return json.dumps({
        "mode": mode,
        "budget": budget,
        "variations_requested": variations,
        "variations_returned": len(top),
        "chains": chains,
        "skipped_chains": skipped,
        "sort_by": sort_by,
        "promos_mode": promos,
        "categories": resolve_categories(categories),
        "combos": top,
    }, ensure_ascii=False, indent=2)
