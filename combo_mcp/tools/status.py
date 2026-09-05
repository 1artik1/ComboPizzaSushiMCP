# -*- coding: utf-8 -*-
"""status.py — статус сетей: fetched_at, возраст, last_error, кол-во позиций."""

import json
import time
from combo_mcp.config import get_chain_meta, get_enabled_chain_ids, get_chain_kind
from combo_mcp.cache import load_cache
from combo_mcp.weights import apply_estimated_weights


def status():
    """Статус всех сетей."""
    meta = get_chain_meta()
    chain_ids = get_enabled_chain_ids()

    result = []
    for c in meta:
        cid = c["id"]
        enabled = cid in chain_ids
        fetched_at = None
        age_seconds = None
        items_count = 0
        items_without_weight = None

        cache_data = load_cache(cid)
        if cache_data:
            fetched_at = cache_data.get("fetched_at")
            items = cache_data.get("items", [])
            items_count = len(items)
            items_without_weight = 0
            if items:
                items, _ = apply_estimated_weights(items, cid)
                items_without_weight = sum(
                    1 for it in items
                    if not (it.get("weight_g") or 0) > 0 and (it.get("price_rub") or 0) > 0
                )
            if fetched_at:
                age_seconds = time.time() - fetched_at

        entry = {
            "id": cid,
            "name": c["name"],
            "kind": get_chain_kind(cid),
            "enabled": enabled,
            "url": c["url"],
            "fetched_at": fetched_at,
            "age_seconds": age_seconds,
            "items_count": items_count,
            "items_without_weight": items_without_weight,
        }
        result.append(entry)

    return json.dumps(result, ensure_ascii=False, indent=2)
