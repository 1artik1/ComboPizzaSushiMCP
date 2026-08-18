# -*- coding: utf-8 -*-
"""list_chains.py — список сетей по кэшу БЕЗ сети; refresh — параллельный парсинг."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from combo_mcp.config import get_chain_meta, get_enabled_chain_ids, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.params import to_bool


def _refresh_chain(cid):
    """Парсинг одной сети для refresh (в отдельном потоке)."""
    try:
        chain_cls = get_chain_class(cid)
        if chain_cls is None:
            return cid, None, None, "Не найден парсер"
        instance = chain_cls()
        items = instance.parse()
        save_cache(cid, items)
        return cid, items, time.time(), None
    except Exception as e:
        return cid, None, None, str(e)


def list_chains(refresh=False):
    """Список доступных сетей доставки."""
    try:
        refresh = to_bool(refresh)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    meta = get_chain_meta()
    chain_ids = get_enabled_chain_ids() if refresh else [c["id"] for c in meta]

    # Параллельный refresh: сети парсятся независимо (свои сессии/кэш-файлы)
    refreshed = {}
    if refresh:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(_refresh_chain, cid): cid for cid in chain_ids}
            for fut in futures:
                cid, items, fetched_at, reason = fut.result()
                refreshed[cid] = (items, fetched_at, reason)

    result = []
    for c in meta:
        cid = c["id"]
        available = False
        items_count = 0
        fetched_at = None
        reason = None

        # Check cache first
        cache_data = load_cache(cid)
        if cache_data:
            fetched_at = cache_data.get("fetched_at")
            items = cache_data.get("items", [])
            items_count = len(items)
            available = bool(items)

        if refresh and cid in refreshed:
            items, fetched_at, reason = refreshed[cid]
            if items is not None:
                items_count = len(items)
                available = True
            elif reason:
                available = False

        entry = {
            "id": cid,
            "name": c["name"],
            "city": c["city"],
            "url": c["url"],
            "available": available,
            "description": c["description"],
        }
        if fetched_at:
            entry["fetched_at"] = fetched_at
        if items_count:
            entry["items_count"] = items_count
        if reason:
            entry["reason"] = reason
        result.append(entry)

    return json.dumps(result, ensure_ascii=False, indent=2)
