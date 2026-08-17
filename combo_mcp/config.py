# -*- coding: utf-8 -*-
"""config.py — загрузка chains_config.json: default-значения + оверрайды."""

import json
import os

_DEFAULTS = {
    "url": "",
    "enabled": True,
    "ttl_minutes": 120,
    "headers": {},
    "cookies": {},
}


def _load_config():
    """Load config from config/chains_config.json relative to this file."""
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "config", "chains_config.json"
    )
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chains": {}}


def get_chain(chain_id):
    """Get config override for a chain, merged with defaults."""
    cfg = _load_config()
    raw = cfg.get("chains", {}).get(chain_id, {})
    merged = dict(_DEFAULTS)
    merged.update(raw)
    return merged


def get_all_chains():
    """Get all chain configs as list of dicts with id added."""
    cfg = _load_config()
    chains = cfg.get("chains", {})
    result = []
    for cid, cdata in chains.items():
        merged = dict(_DEFAULTS)
        merged.update(cdata)
        merged["id"] = cid
        result.append(merged)
    return result


def get_enabled_chain_ids():
    """Get list of enabled chain IDs."""
    cfg = _load_config()
    chains = cfg.get("chains", {})
    return [cid for cid, cdata in chains.items() if cdata.get("enabled", True)]


def get_extra_refresh_at():
    """Время суток ежедневного обновления доп. данных ("HH:MM"), по умолчанию "11:00"."""
    cfg = _load_config()
    val = cfg.get("extra_refresh_at", "11:00")
    if not (isinstance(val, str) and len(val) == 5 and val[2] == ":"
            and val[:2].isdigit() and val[3:].isdigit()):
        return "11:00"
    return val


def get_chain_meta():
    """Get chain metadata (id, name, city, url, description)."""
    return [
        {
            "id": "la_pizza",
            "name": "Ла Пицца",
            "city": "Воронеж",
            "url": "https://la-pizza.pro",
            "description": "Сеть доставки пиццы. Каталог: обычные, гигант, римские + комбо.",
        },
        {
            "id": "pizza_kuba",
            "name": "Пицца Куба",
            "city": "Воронеж",
            "url": "https://pizzeriacuba.ru",
            "description": "Пиццерия с доставкой.",
        },
        {
            "id": "ninja_food",
            "name": "Ниндзя Фуд",
            "city": "Воронеж",
            "url": "https://ninjafood.su",
            "description": "Bitrix-сайт. Пицца, роллы, сеты, вок, ланчи.",
        },
        {
            "id": "sushi_time",
            "name": "Сушитайм",
            "city": "Воронеж",
            "url": "https://суши-тайм.рф/Voronezh/",
            "description": "Доставка роллов и суши.",
        },
        {
            "id": "sushi_darom",
            "name": "Суши Даром",
            "city": "Воронеж",
            "url": "https://voronezh.sushi-darom.com",
            "description": "Сеть роллов и суши. Next.js-приложение.",
        },
        {
            "id": "anti_sushi",
            "name": "Антисуши",
            "city": "Воронеж",
            "url": "https://anti-sushi.ru",
            "description": "Бренд-сестра Суши Даром. Пицца, роллы, суши, сеты.",
        },
        {
            "id": "dodo",
            "name": "Додо Пицца",
            "city": "Воронеж",
            "url": "https://dodopizza.ru",
            "description": "Крупная сеть. API может быть заблокирован капчей.",
        },
    ]


def get_chain_class(chain_id):
    """Получить класс парсера по id (из chains реестра)."""
    try:
        from combo_mcp.chains.base import _CHAIN_REGISTRY
        return _CHAIN_REGISTRY.get(chain_id)
    except ImportError:
        return None


def get_registered_chain_classes():
    """Получить все зарегистрированные chain-классы."""
    try:
        from combo_mcp.chains.base import _CHAIN_REGISTRY
        return dict(_CHAIN_REGISTRY)
    except ImportError:
        return {}
