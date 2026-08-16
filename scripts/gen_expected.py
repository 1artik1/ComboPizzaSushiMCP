# -*- coding: utf-8 -*-
"""Одноразовая генерация tests/expected.json: эталоны комбо для всех сетей.

Вызывает best_combo напрямую (из кэша, refresh=False), как это делает autotest.
"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())

from combo_mcp.config import get_chain_meta
from combo_mcp.tools.best_combo import best_combo

BUDGETS = [1500, 3000]
PERSONS = [1, 2]

out = {"version": 1, "combos": {}}
for c in get_chain_meta():
    cid = c["id"]
    out["combos"][cid] = {}
    for budget in BUDGETS:
        for persons in PERSONS:
            raw = json.loads(best_combo(cid, budget, persons=persons, variations=3, refresh=False))
            key = f"{budget}_{persons}"
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

os.makedirs("tests", exist_ok=True)
with open("tests/expected.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("written: tests/expected.json")