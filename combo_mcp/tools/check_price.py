# -*- coding: utf-8 -*-
"""check_price.py — check_price(chain_id, item_name, expected_price=None)."""

import json
from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.cache import save_cache
from combo_mcp.chains.base import ChainUnavailable
from combo_mcp.weights import apply_estimated_weights
from combo_mcp.params import to_int


def check_price(chain_id, item_name, expected_price=None):
    """Проверка цены позиции."""
    ids = [c["id"] for c in get_chain_meta()]
    chain_id = (chain_id or "").strip()
    if chain_id not in ids:
        return json.dumps({"error": f"Неизвестная сеть '{chain_id}'"}, ensure_ascii=False)

    if expected_price not in (None, ""):
        try:
            expected_price = to_int(expected_price, "expected_price", minimum=0)
        except ValueError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    else:
        expected_price = None

    if not item_name or not str(item_name).strip():
        return json.dumps({"error": "item_name обязателен"}, ensure_ascii=False)

    # Fresh parse
    try:
        chain_cls = get_chain_class(chain_id)
        if chain_cls is None:
            return json.dumps({"error": f"Не найден парсер для {chain_id}"}, ensure_ascii=False)
        instance = chain_cls()
        items = instance.parse()
        save_cache(chain_id, items)
    except ChainUnavailable as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    # Apply reference book for items without weight
    items, _ = apply_estimated_weights(items, chain_id)

    # Find by substring
    matches = [it for it in items if item_name.lower() in it["name"].lower()]

    if not matches:
        return json.dumps({
            "chain_id": chain_id,
            "item_name": item_name,
            "found": False,
            "matches": [],
        }, ensure_ascii=False, indent=2)

    results = []
    for it in matches:
        entry = {
            "name": it["name"],
            "weight_g": it.get("weight_g"),
            "weight_source": it.get("weight_source", "none"),
            "price_rub": it["price_rub"],
            "found": True,
        }
        if expected_price is not None:
            if it["price_rub"] == expected_price:
                entry["match"] = True
                entry["message"] = f"Цена совпадает: {expected_price}₽"
            else:
                entry["match"] = False
                entry["message"] = f"Расхождение: найдено {it['price_rub']}₽, ожидалось {expected_price}₽"
        results.append(entry)

    return json.dumps(results, ensure_ascii=False, indent=2)
