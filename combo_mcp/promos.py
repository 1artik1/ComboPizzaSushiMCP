# -*- coding: utf-8 -*-
"""promos.py — правила промо-скидок для комбо."""

import json
import os
import datetime

_PROMOS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "promos.json",
)


def load_promo_rules(chain_id):
    """Загрузить список правил промо для сети из config/promos.json."""
    try:
        with open(_PROMOS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return data.get(chain_id, []) or []


def apply_promos(chain_id, price_rub, mode="", item_categories=None):
    """Применить промо-правила к цене комбо.

    Возвращает dict:
    {
        "promo_price": int,
        "saved": int,
        "promos": [
            {id, title, type, scope, value, saved, once?, per_item?, source?},
            ...
        ]
    }
    """
    rules = load_promo_rules(chain_id)
    if not rules:
        return {"promo_price": price_rub, "saved": 0, "promos": []}

    # Фильтруем правила по mode, пропускаем delivery
    applicable = []
    for r in rules:
        scope = r.get("scope", "")
        if scope == "delivery":
            continue
        if mode == "" and r.get("scope") != "":
            continue
        if mode == "order" and r.get("scope") != "order":
            continue
        if mode == "pickup" and r.get("scope") != "pickup":
            continue
        applicable.append(r)

    # Проверяем каждое правило
    candidates = []
    for r in applicable:
        # min_order
        min_order = r.get("min_order")
        if min_order is not None and price_rub < min_order:
            continue
        # days
        days = r.get("days")
        if days is not None:
            today = datetime.datetime.today().weekday()
            if today not in days:
                continue
        # items
        rule_items = r.get("items")
        per_item = r.get("per_item", False)
        if rule_items and item_categories:
            if per_item:
                match_count = sum(1 for g in item_categories if g in rule_items)
                if match_count == 0:
                    continue
            else:
                if not any(g in rule_items for g in item_categories):
                    continue

        # Вычисляем saved
        if r["type"] == "fixed":
            base_saved = r["value"]
        elif r["type"] == "percent":
            base_saved = round(price_rub * r["value"] / 100)
        elif r["type"] == "cashback":
            base_saved = round(price_rub * r["value"] / 100)
        else:
            base_saved = 0

        if per_item and rule_items and item_categories:
            match_count = sum(1 for g in item_categories if g in rule_items)
            saved = base_saved * match_count
        else:
            saved = base_saved

        candidates.append({
            "rule": r,
            "saved": saved,
            "per_item": per_item,
        })

    # Несуммируемость: stackable=false конкурируют (лучший saved)
    non_stackable = [c for c in candidates if not c["rule"].get("stackable", False)]
    stackable = [c for c in candidates if c["rule"].get("stackable", False)]

    best_ns = None
    if non_stackable:
        best_ns = max(non_stackable, key=lambda x: x["saved"])

    # promo_price = max(price - saved_non_cashback, 0)
    total_nc = 0
    if best_ns and best_ns["rule"]["type"] != "cashback":
        total_nc += best_ns["saved"]
    for s in stackable:
        if s["rule"]["type"] != "cashback":
            total_nc += s["saved"]
    promo_price = max(price_rub - total_nc, 0)

    # Строим promos-список
    promos = []
    if best_ns:
        promos.append(_promo_dict(best_ns))
    for s in stackable:
        promos.append(_promo_dict(s))

    # Порядок: скидки по уб. saved, потом cashback
    discounts = [p for p in promos if p["type"] != "cashback"]
    cashback = [p for p in promos if p["type"] == "cashback"]
    discounts.sort(key=lambda x: -x["saved"])
    promos = discounts + cashback

    return {"promo_price": promo_price, "saved": total_nc, "promos": promos}


def _promo_dict(c):
    """Сформировать dict правила для ответа."""
    r = c["rule"]
    p = {
        "id": r["id"],
        "title": r["title"],
        "type": r["type"],
        "scope": r["scope"],
        "value": r["value"],
        "saved": c["saved"],
    }
    if r.get("once"):
        p["once"] = True
    if r.get("per_item"):
        p["per_item"] = True
    if r.get("source"):
        p["source"] = r["source"]
    return p
