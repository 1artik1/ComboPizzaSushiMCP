# -*- coding: utf-8 -*-
"""server.py — MCP Server (MCPServer) + 13 инструментов."""

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

# Create server
mcp = MCPServer(
    "combo-engine",
    version="1.0.0",
    title="Combo Engine",
    description="Расчёт выгодных комбо по сетям доставки в Воронеже",
)

# Register all 13 tools
mcp.add_tool(
    _list_chains,
    name="list_chains",
    description="Список доступных сетей доставки: id, название, город, available, описание.",
)

mcp.add_tool(
    _parse_menu,
    name="parse_menu",
    description="Распарсить меню конкретной сети.",
)

mcp.add_tool(
    _best_combo,
    name="best_combo",
    description="Лучшие 3 варианта комбо для сети при заданном бюджете.",
)

mcp.add_tool(
    _compare,
    name="compare",
    description="Сравнить все доступные сети по лучшему комбо при заданном бюджете.",
)

mcp.add_tool(
    _status,
    name="status",
    description="Конфиг: сети enabled/disabled; по каждой: fetched_at, возраст, last_error, кол-во позиций.",
)

mcp.add_tool(
    _verify_chain,
    name="verify_chain",
    description="verify_chain: кол-во позиций, с весом/без, от-цены, дубликаты, аномалии.",
)

mcp.add_tool(
    _check_price,
    name="check_price",
    description="check_price: свежий парсинг, поиск по подстроке, проверка цены.",
)

mcp.add_tool(
    _diff_menu,
    name="diff_menu",
    description="diff_menu: сравнение items vs prev_items — добавлено/удалено/изменение цены.",
)

mcp.add_tool(
    _check_config,
    name="check_config",
    description="check_config: валидация chains_config.json.",
)

mcp.add_tool(
    _health_check,
    name="health_check",
    description="health_check: стабильность получения данных с сайтов — HTTP, парсинг, кол-во позиций.",
)

mcp.add_tool(
    _chain_info,
    name="chain_info",
    description="chain_info: доставка, акции, лояльность сети (обновление раз в день в extra_refresh_at).",
)

mcp.add_tool(
    _help_tool,
    name="help",
    description="help: список команд combo-engine (13), пагинация /help next|back, детали /help <команда>.",
)

mcp.add_tool(
    _favorites,
    name="favorites",
    description="favorites: избранное — сохранить понравившееся комбо (add), список (list), удалить (remove), очистить (clear).",
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
