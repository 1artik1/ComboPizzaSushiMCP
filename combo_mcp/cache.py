# -*- coding: utf-8 -*-
"""cache.py — дисковый кэш: cache/<chain>.json = {fetched_at, items[], prev_items[]}."""

import json
import os
import tempfile
import time

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")


def _cache_path(chain_id):
    """Get cache file path for a chain."""
    return os.path.join(_CACHE_DIR, f"{chain_id}.json")


def load_cache(chain_id):
    """Load cached items for a chain. Returns {fetched_at, items, prev_items} or None."""
    path = _cache_path(chain_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, KeyError):
        return None


def save_cache(chain_id, items):
    """Save items to cache file. Moves current items to prev_items.

    Атомарная запись: tempfile + os.replace (без битых файлов при сбое).
    """
    os.makedirs(_CACHE_DIR, exist_ok=True)
    path = _cache_path(chain_id)
    prev = None
    if os.path.exists(path):
        prev_data = load_cache(chain_id)
        if prev_data:
            prev = prev_data.get("items", [])
    data = {
        "fetched_at": time.time(),
        "items": items,
        "prev_items": prev,
    }
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=_CACHE_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return data


def is_cache_stale(chain_id, ttl_minutes):
    """Check if cache is stale based on TTL."""
    data = load_cache(chain_id)
    if data is None:
        return True
    age = time.time() - data.get("fetched_at", 0)
    return age > ttl_minutes * 60


def load_items_with_ttl(chain_id):
    """Items из кэша, если он не устарел по menu_ttl_minutes сети.

    menu_ttl_minutes=0 (по умолчанию) — кэш считается бессрочным (текущее
    поведение); >0 — при возрасте больше TTL возвращает None (нужен свежий парсинг).
    """
    from combo_mcp.config import get_chain
    ttl = get_chain(chain_id).get("menu_ttl_minutes", 0) or 0
    if ttl > 0 and is_cache_stale(chain_id, ttl):
        return None
    data = load_cache(chain_id)
    return data.get("items", []) if data else None


def clear_cache():
    """Remove menu cache files.

    НЕ трогает favorites.json и extra_*.json (избранное и доп. данные).
    """
    if os.path.exists(_CACHE_DIR):
        for fn in os.listdir(_CACHE_DIR):
            if fn.endswith(".json") and not fn.startswith("extra_") \
                    and fn != "favorites.json":
                os.remove(os.path.join(_CACHE_DIR, fn))
