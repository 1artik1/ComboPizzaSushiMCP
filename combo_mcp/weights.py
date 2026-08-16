# -*- coding: utf-8 -*-
"""weights.py — справочник расчётных весов (config/estimated_weights.json).

Применяется к позициям без веса от парсера:
- weight_g берётся из справочника (поле weight_g),
- weight_source = "reference",
- источник указывается в поле source.

weight_source возможные значения:
- site      — вес указан на сайте/в API сети (парсер)
- size_name — вес из названия размера (pizza_kuba)
- reference — вес из справочника estimated_weights.json
- none      — вес отсутствует
"""

import json
import os

_ESTIMATED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "estimated_weights.json",
)


def load_estimated_weights():
    """Загрузить справочник: {"chains": {"<id>": {"items": {name: {weight_g, source}}}}}."""
    try:
        with open(_ESTIMATED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data.get("chains", {}) or {}


def get_estimated_weight(chain_id, name):
    """Вес и источник для позиции из справочника, или None."""
    entry = load_estimated_weights().get(chain_id, {}).get("items", {}).get(name)
    if entry and entry.get("weight_g"):
        return {"weight_g": int(entry["weight_g"]), "source": entry.get("source", "справочник")}
    return None


def apply_estimated_weights(items, chain_id):
    """Проставить weight_source и расчётные веса позициям.

    Возвращает (items, estimated_count): items — список словарей с полем
    weight_source; estimated_count — сколько позиций получили вес из справочника.
    """
    estimated_count = 0
    result = []
    for it in items:
        item = dict(it)
        w = item.get("weight_g")
        has_weight = w is not None and w > 0
        if has_weight:
            item["weight_source"] = item.get("weight_source") or "site"
        else:
            est = get_estimated_weight(chain_id, item.get("name", ""))
            if est:
                item["weight_g"] = est["weight_g"]
                item["weight_source"] = "reference"
                item["weight_source_name"] = est["source"]
                estimated_count += 1
            else:
                item["weight_source"] = "none"
        result.append(item)
    return result, estimated_count