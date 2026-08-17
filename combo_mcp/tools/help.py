# -*- coding: utf-8 -*-
"""help.py — help_tool(action, command): справочник команд combo-engine с пагинацией."""

import json
import math

# Глобальное состояние (одна сессия MCP stdio)
_help_page = 1
PAGE_SIZE = 10

COMMANDS = [
    {
        "name": "list_chains",
        "args": "(refresh=)",
        "description": "Список доступных сетей доставки: id, название, город, available, описание",
        "example": "list_chains",
    },
    {
        "name": "parse_menu",
        "args": "(chain_id, category=, min_weight=, sort_by=, limit=, refresh=)",
        "description": "Распарсить меню сети с фильтрами и сортировкой",
        "example": 'parse_menu "pizza_kuba" limit=10',
    },
    {
        "name": "best_combo",
        "args": "(chain_id, budget, persons=1, variations=3, refresh=, categories=)",
        "description": "Лучшие варианты комбо для сети при заданном бюджете",
        "example": 'best_combo "anti_sushi" 2000 persons=2 categories="пицца"',
    },
    {
        "name": "compare",
        "args": "(budget, persons=1, categories=)",
        "description": "Сравнить все сети по лучшему комбо при заданном бюджете",
        "example": 'compare 2000 persons=2 categories="пицца"',
    },
    {
        "name": "status",
        "args": "()",
        "description": "Конфиг и кэш: сети, возраст данных, ошибки",
        "example": "status",
    },
    {
        "name": "verify_chain",
        "args": "(chain_id)",
        "description": "Качество данных сети: веса, дубликаты, аномалии",
        "example": 'verify_chain "dodo"',
    },
    {
        "name": "check_price",
        "args": "(chain_id, item_name, expected_price=)",
        "description": "Свежий парсинг и проверка цены позиции",
        'example': 'check_price "sushi_time" "Дружба"',
    },
    {
        "name": "diff_menu",
        "args": "(chain_id)",
        "description": "Изменения меню с прошлой загрузки",
        "example": 'diff_menu "ninja_food"',
    },
    {
        "name": "check_config",
        "args": "()",
        "description": "Валидация chains_config.json",
        "example": "check_config",
    },
    {
        "name": "health_check",
        "args": "(refresh=)",
        "description": "Стабильность получения данных с сайтов",
        "example": "health_check",
    },
    {
        "name": "chain_info",
        "args": "(chain_id, refresh=)",
        "description": "Доставка, акции, лояльность сети",
        "example": 'chain_info "la_pizza"',
    },
    {
        "name": "help",
        "args": "(action=, command=)",
        "description": "Список команд combo-engine с описаниями",
        "example": "/help, /help best_combo",
    },
    {
        "name": "favorites",
        "args": "(action=, chain_id=, label=, items=, query=)",
        "description": "Избранное: сохранить/показать/удалить понравившееся комбо",
        'example': 'favorites action="list"',
    },
]

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
            "hint": "next — следующая страница, back — назад, /help <команда> — детали команды",
        },
        ensure_ascii=False,
        indent=2,
    )
