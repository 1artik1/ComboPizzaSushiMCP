# -*- coding: utf-8 -*-
"""selftest.py — парсит все сети, 3 комбо при 3000, compare.

Запуск: python scripts\\selftest.py
Результат: mcp_selftest.txt в .venv\\project\\
"""

import sys
import os
import codecs
import json

# Ensure project dir is in path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_script_dir)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from combo_mcp.config import get_chain_meta, get_enabled_chain_ids
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import get_chain_class, ChainUnavailable
from combo_mcp.engines.dp import calculate_combos
from combo_mcp.engines.taste import count_ingredients
from combo_mcp.tools.compare import compare as _compare


def run_selftest():
    budget = 3000
    print(f"\n{'='*60}")
    print(f"  COMBO ENGINE SELF-TEST  (budget={budget} rub)")
    print(f"{'='*60}\n")

    results = []
    for c in get_chain_meta():
        cid = c["id"]
        print(f"\n--- {c['name']} ({cid}) ---")
        try:
            # Try cache first
            cache_data = load_cache(cid)
            if cache_data:
                items = cache_data.get("items", [])
            else:
                chain_cls = get_chain_class(cid)
                if chain_cls:
                    instance = chain_cls()
                    items = instance.parse()
                    save_cache(cid, items)
                else:
                    items = []

            print(f"  Parsed: {len(items)} items")
            for it in items[:5]:
                w = it.get("weight_g", "N/A")
                p = it.get("price_rub", "N/A")
                cat = it.get("category", "N/A")
                print(f"  {it['name']} | {w}g | {p}rub | {cat}")

            # Filter valid items (weight>0 AND price>0)
            no_weight = 0
            no_price = 0
            valid_items = []
            for it in items:
                w = it.get("weight_g")
                p = it.get("price_rub")
                if p is not None and p > 0:
                    if w is not None and w > 0:
                        valid_items.append(dict(it))
                    else:
                        no_weight += 1
                else:
                    no_price += 1

            print(f"  Valid (weight>0,price>0): {len(valid_items)}, excluded: {no_weight + no_price} (w:{no_weight} p:{no_price})")

            if not valid_items:
                print(f"  SKIP: нет позиций с весом")
                results.append({"chain": cid, "status": "NO_WEIGHT", "items": len(items), "valid": 0, "excluded": no_weight})
                continue

            # Calculate combos
            lines = calculate_combos(valid_items, budget, persons=1, variations=3)
            for i, line in enumerate(lines, 1):
                print(f"  {i}) {line}")
            results.append({"chain": cid, "status": "OK", "items": len(items), "valid": len(valid_items), "excluded": no_weight, "lines": lines})

        except ChainUnavailable as e:
            print(f"  UNAVAILABLE: {e}")
            results.append({"chain": cid, "status": "UNAVAILABLE", "items": 0, "error": str(e)})
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"chain": cid, "status": "ERROR", "items": 0, "error": str(e)})

    # --- COMPARE ---
    print(f"\n{'='*60}")
    print(f"  COMPARE (budget={budget} rub)")
    print(f"{'='*60}")

    try:
        compare_result = _compare(budget)
        compare_data = json.loads(compare_result)
        for i, comp in enumerate(compare_data, 1):
            name = comp.get("name", "Unknown")
            available = comp.get("available", False)
            if available:
                weight = comp.get("total_weight_g", 0)
                price = comp.get("total_price_rub", 0)
                pp100 = comp.get("price_per_100g", 0)
                num_items = comp.get("num_items", 0)
                print(f"  {i}. {name}: {weight}g | {price}rub | {round(pp100, 2)} rub/100g | {num_items} items")
            else:
                error = comp.get("error", "Unknown")
                print(f"  {i}. {name}: ERROR - {error}")
    except Exception as e:
        print(f"  COMPARE ERROR: {e}")

    # Save results
    output_path = os.path.join(_project_dir, "mcp_selftest.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(results, ensure_ascii=False, indent=2))

    print(f"\nSelftest saved to {output_path}\n")
    print("DONE")


if __name__ == "__main__":
    run_selftest()
