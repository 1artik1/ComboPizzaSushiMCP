# -*- coding: utf-8 -*-
"""base.py — декоратор @tool(name, description, schema) + реестр TOOLS."""

import json

_REGISTRY = {}


def tool(name, description="", schema=None):
    """Декоратор для регистрации инструмента MCP.

    Args:
        name: имя инструмента
        description: описание
        schema: dict с описанием аргументов {"arg1": {"type": "string", "description": "..."}}
    """
    def decorator(func):
        _REGISTRY[name] = {
            "name": name,
            "description": description,
            "schema": schema or {},
            "handler": func,
        }
        return func
    return decorator


def get_tools():
    """Получить все зарегистрированные инструменты."""
    return dict(_REGISTRY)


def call_tool(name, arguments=None):
    """Вызвать инструмент по имени с аргументами."""
    tool_info = _REGISTRY.get(name)
    if tool_info is None:
        return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
    handler = tool_info["handler"]
    try:
        result = handler(**(arguments or {}))
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
