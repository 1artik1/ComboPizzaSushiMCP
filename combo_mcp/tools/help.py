# -*- coding: utf-8 -*-
"""help.py — help_tool(action, command): справочник команд combo-engine с пагинацией.

Описания команд — единый реестр combo_mcp/tools/meta.py.
"""

import json
import math

from combo_mcp.tools.meta import TOOLS_META

# Глобальное состояние (одна сессия MCP stdio)
_help_page = 1
PAGE_SIZE = 10

COMMANDS = list(TOOLS_META)

_TOTAL_COMMANDS = len(COMMANDS)
_TOTAL_PAGES = math.ceil(_TOTAL_COMMANDS / PAGE_SIZE)


def help_tool(action="", command=""):
    """Справочник команд combo-engine с пагинацией и деталями.

    action: "next" / "back" для листания страниц.
    command: имя команды для показа деталей (точное совпадение, регистронезависимо).
    """
    # Если указана команда — показать детали
    if command:
        cmd_lower = command.lower().strip()
        for c in COMMANDS:
            if c["name"].lower() == cmd_lower:
                return json.dumps(
                    {"command": c}, ensure_ascii=False, indent=2
                )
        return json.dumps(
            {"error": "Команда не найдена. /help — список команд"},
            ensure_ascii=False,
        )

    # Пагинация
    global _help_page
    if action == "next":
        _help_page = min(_help_page + 1, _TOTAL_PAGES)
    elif action == "back":
        _help_page = max(_help_page - 1, 1)
    else:
        _help_page = 1

    start = (_help_page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = COMMANDS[start:end]

    return json.dumps(
        {
            "page": _help_page,
            "total_pages": _TOTAL_PAGES,
            "total_commands": _TOTAL_COMMANDS,
            "commands": [
                {"name": c["name"], "args": c["args"], "description": c["description"]}
                for c in page_items
            ],
            "hint": "next — следующая страница, back — назад, /help <команда> — детали команды. Смысл и сценарии команд — в COMMANDS.md",
        },
        ensure_ascii=False,
        indent=2,
    )
