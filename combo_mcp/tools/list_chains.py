# -*- coding: utf-8 -*-
"""list_chains.py — список сетей по кэшу БЕЗ сети."""

import json
import time
from combo_mcp.config import get_chain_meta, get_enabled_chain_ids, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable


def list_chains(refresh=False):
    """Список доступных сетей доставки."""
    meta = get_chain_meta()
    chain_ids = get_enabled_chain_ids() if refresh else [c["id"] for c in meta]

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

        if refresh and cid in chain_ids:
            # Try to parse
            try:
                chain_cls = get_chain_class(cid)
                if chain_cls:
                    instance = chain_cls()
                    items = instance.parse()
                    save_cache(cid, items)
                    items_count = len(items)
                    fetched_at = time.time()
                    available = True
                else:
                    available = False
                    reason = "Не найден парсер"
            except ChainUnavailable as e:
                reason = str(e)
            except Exception as e:
                reason = str(e)

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
