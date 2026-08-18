# -*- coding: utf-8 -*-
"""params.py — конвертация строковых параметров MCP-тулов.

Все параметры приходят от MCP СТРОКАМИ (JSON-схема type: string).
Никогда не сравнивать строку с int/float напрямую — сначала конвертация.
"""


def to_bool(value, default=False):
    """Привести строку/буль к bool.

    "1"/"true"/"yes"/"on" -> True; "0"/"false"/"no"/"off" -> False;
    None/"" -> default. Нераспознанное значение -> ValueError.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("", "none", "null"):
        return default
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"ожидалось true/false, получено: {value!r}")


def to_int(value, name="параметр", minimum=None):
    """Привести строку/число к int. Невалидное значение -> ValueError.

    minimum — если задано и результат меньше — ValueError.
    """
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name} должен быть целым числом, получено: {value!r}")
    try:
        result = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{name} должен быть целым числом, получено: {value!r}")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} должен быть >= {minimum}, получено: {result}")
    return result


def to_float(value, name="параметр", minimum=None):
    """Привести строку/число к float. Невалидное значение -> ValueError."""
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name} должен быть числом, получено: {value!r}")
    try:
        result = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"{name} должен быть числом, получено: {value!r}")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} должен быть >= {minimum}, получено: {result}")
    return result