# -*- coding: utf-8 -*-
"""meta.py — единый реестр описаний MCP-инструментов.

Источник правды для server.py (описания при регистрации) и help.py
(справочник команд). Держать поля консистентными с сигнатурами тулов.
"""

TOOLS_META = [
    {
        "name": "list_chains",
        "args": "(refresh=)",
        "description": "Список сетей доставки: id, название, город, available (есть данные в кэше), описание",
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
        "args": "(chain_id, budget, persons=1, variations=3, refresh=, categories=, promos=)",
        "description": "Лучшие варианты комбо для сети при заданном бюджете. promos: order/pickup/all для применения скидок",
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
        "example": 'check_price "sushi_time" "Дружба"',
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
        "example": 'favorites action="list"',
    },
]

# name -> описание (для регистрации тулов в server.py)
TOOLS_DESCRIPTIONS = {t["name"]: t["description"] for t in TOOLS_META}
