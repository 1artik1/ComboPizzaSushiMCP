# -*- coding: utf-8 -*-
"""Генерация tests/expected.json: эталоны комбо для всех сетей.

Вызывает best_combo напрямую (из кэша, refresh=False), как это делает autotest.
Раздел "dishes" (контрольные блюда) сохраняется из текущего файла — комбо
пересоздаются, блюда остаются прежними.
"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())

from combo_mcp.config import get_chain_meta
from combo_mcp.tools.best_combo import best_combo

BUDGETS = [1500, 3000]
PATH = "tests/expected.json"

old = {}
if os.path.exists(PATH):
    try:
        with open(PATH, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}

out = {"version": 1, "combos": {}}
for c in get_chain_meta():
    cid = c["id"]
    out["combos"][cid] = {}
    for budget in BUDGETS:
        raw = json.loads(best_combo(cid, budget, variations=3, refresh=False))
        key = str(budget)
        if "error" in raw:
            out["combos"][cid][key] = {"error": raw["error"]}
        else:
            out["combos"][cid][key] = [
                {
                    "weight_g": v["weight_g"],
                    "price_rub": v["price_rub"],
                    "price_per_100g": v["price_per_100g"],
                    "items": v["items"],
                }
                for v in raw["combos"]
            ]

if isinstance(old.get("dishes"), dict):
    out["dishes"] = old["dishes"]

os.makedirs("tests", exist_ok=True)
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("written: tests/expected.json")