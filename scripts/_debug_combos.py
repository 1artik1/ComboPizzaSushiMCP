# Debug combo calculation error
import sys, os, codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

_project_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_project_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from combo_mcp.chains.base import get_chain_class
from combo_mcp.engines.dp import calculate_combos

# Test dodo
print("Testing dodo...")
cls = get_chain_class("dodo")
if cls:
    instance = cls()
    items = instance.parse()
    print(f"Parsed {len(items)} items")
    valid = [i for i in items if i.get("weight_g") and i["weight_g"] > 0]
    print(f"Valid (weight>0): {len(valid)}")
    # Try calculate_combos
    try:
        for i, line in enumerate(calculate_combos(valid, 3000), 1):
            print(f"Line{i}: {line}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

print()
print("Testing pizza_kuba...")
cls = get_chain_class("pizza_kuba")
if cls:
    instance = cls()
    items = instance.parse()
    print(f"Parsed {len(items)} items")
    valid = [i for i in items if i.get("weight_g") and i["weight_g"] > 0]
    print(f"Valid (weight>0): {len(valid)}")
    try:
        for i, line in enumerate(calculate_combos(valid, 3000), 1):
            print(f"Line{i}: {line}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
