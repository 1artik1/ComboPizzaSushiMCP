# -*- coding: utf-8 -*-
"""config.py — загрузка chains_config.json: default-значения + оверрайды."""

import json
import os

_KIND_COMBO = "combo"
_KIND_STORE = "store"

_DEFAULTS = {
    "url": "",
    "enabled": True,
    "kind": _KIND_COMBO,
    "http_timeout": 10,
    "menu_ttl_minutes": 0,
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


def get_chain_kind(chain_id):
    """Тип сети: 'combo' (рестораны доставки) или 'store' (магазины, поиск товаров)."""
    return get_chain(chain_id).get("kind", _KIND_COMBO)


def get_combo_chain_ids():
    """Id включённых сетей-ресторанов (kind=combo) — участники комбо/сравнения."""
    cfg = _load_config()
    chains = cfg.get("chains", {})
    return [
        cid for cid, cdata in chains.items()
        if cdata.get("enabled", True) and cdata.get("kind", _KIND_COMBO) == _KIND_COMBO
    ]


def get_store_chain_ids():
    """Id включённых магазинов (kind=store) — для store_search/store_categories."""
    cfg = _load_config()
    chains = cfg.get("chains", {})
    return [
        cid for cid, cdata in chains.items()
        if cdata.get("enabled", True) and cdata.get("kind", _KIND_STORE) == _KIND_STORE
    ]


def get_extra_refresh_at():
    """Время суток ежедневного обновления доп. данных ("HH:MM"), по умолчанию "11:00"."""
    cfg = _load_config()
    val = cfg.get("extra_refresh_at", "11:00")
    if not (isinstance(val, str) and len(val) == 5 and val[2] == ":"
            and val[:2].isdigit() and val[3:].isdigit()):
        return "11:00"
    return val


def get_chain_meta():
    """Собрать метаданные сетей из реестра парсеров.

    Возвращает список dict с полями id/name/city/url/description.
    """
    try:
        from combo_mcp.chains.base import _CHAIN_REGISTRY
    except ImportError:
        return []

    result = []
    for cid, cls in _CHAIN_REGISTRY.items():
        result.append({
            "id": cid,
            "name": getattr(cls, "name", cid),
            "city": getattr(cls, "city", "Воронеж"),
            "url": getattr(cls, "url", ""),
            "description": getattr(cls, "description", ""),
        })
    return result


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
