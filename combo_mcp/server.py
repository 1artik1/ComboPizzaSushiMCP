# -*- coding: utf-8 -*-
"""server.py — MCP Server (MCPServer) + 15 инструментов.

Описания инструментов — единый реестр combo_mcp/tools/meta.py.
"""

import sys
import os

# Ensure our project directory is in sys.path
_project_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_project_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from mcp.server.mcpserver import MCPServer

# Import all tool functions
from combo_mcp.tools.list_chains import list_chains as _list_chains
from combo_mcp.tools.parse_menu import parse_menu as _parse_menu
from combo_mcp.tools.best_combo import best_combo as _best_combo
from combo_mcp.tools.compare import compare as _compare
from combo_mcp.tools.status import status as _status
from combo_mcp.tools.verify_chain import verify_chain as _verify_chain
from combo_mcp.tools.check_price import check_price as _check_price
from combo_mcp.tools.diff_menu import diff_menu as _diff_menu
from combo_mcp.tools.check_config import check_config as _check_config
from combo_mcp.tools.health_check import health_check as _health_check
from combo_mcp.tools.chain_info import chain_info as _chain_info
from combo_mcp.tools.help import help_tool as _help_tool
from combo_mcp.tools.favorites import favorites as _favorites
from combo_mcp.tools.store_search import store_search as _store_search
from combo_mcp.tools.store_categories import store_categories as _store_categories

from combo_mcp.tools.meta import TOOLS_META

# Create server
mcp = MCPServer(
    "combo-engine",
    version="1.3.0",
    title="Combo Engine",
    description="Расчёт выгодных комбо по сетям доставки в Воронеже",
)

# Реестр хендлеров: имя -> функция (из tools/*.py)
_HANDLERS = {
    "list_chains": _list_chains,
    "parse_menu": _parse_menu,
    "best_combo": _best_combo,
    "compare": _compare,
    "status": _status,
    "verify_chain": _verify_chain,
    "check_price": _check_price,
    "diff_menu": _diff_menu,
    "check_config": _check_config,
    "health_check": _health_check,
    "chain_info": _chain_info,
    "help": _help_tool,
    "favorites": _favorites,
    "store_search": _store_search,
    "store_categories": _store_categories,
}

# Register all tools from the single meta registry
for _t in TOOLS_META:
    _handler = _HANDLERS.get(_t["name"])
    if _handler is not None:
        mcp.add_tool(
            _handler,
            name=_t["name"],
            description=_t["description"],
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("Запустите: python scripts\\selftest.py")
        sys.exit(0)

    # Run as MCP stdio server
    import asyncio

    asyncio.run(mcp.run_stdio_async())
