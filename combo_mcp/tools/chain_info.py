# -*- coding: utf-8 -*-
"""chain_info.py — chain_info(chain_id, refresh=False): доставка, акции, лояльность.

Берёт доп. информацию из extra-кэша (обновление раз в день в момент
extra_refresh_at из chains_config.json, по умолчанию 11:00), при ошибке —
старый срез с пометкой stale.
"""

import json
import time
import datetime

from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.extra_cache import get_extra
from combo_mcp import config as mcp_config
from combo_mcp.params import to_bool


def chain_info(chain_id, refresh=False):
    """Доп. информация сети: доставка, акции, лояльность + метаданные.

    refresh=True — принудительно перепарсить страницы сети сейчас.
    """
    chain_id = (chain_id or "").strip()
    if not chain_id:
        return json.dumps({"error": "Не указан chain_id"}, ensure_ascii=False)

    try:
        refresh = to_bool(refresh)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    meta = {c["id"]: c for c in get_chain_meta()}
    if chain_id not in meta:
        available = ", ".join(sorted(meta))
        return json.dumps({
            "error": f"Неизвестная сеть '{chain_id}'. Доступны: {available}",
        }, ensure_ascii=False)

    if get_chain_class(chain_id) is None:
        return json.dumps({"error": f"Парсер для '{chain_id}' не найден"},
                          ensure_ascii=False)

    res = get_extra(chain_id, refresh=refresh)
    extra = res.get("extra") or {}

    info = {
        "id": chain_id,
        "name": meta[chain_id]["name"],
        "city": meta[chain_id].get("city"),
        "extra_refresh_at": mcp_config.get_extra_refresh_at(),
        "source_state": res.get("source_state"),
        "updated": res.get("updated", False),
        "checked_at": res.get("fetched_at"),
        "last_error": res.get("last_error"),
    }
    if info.get("checked_at"):
        info["checked_at"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(info["checked_at"]))

    for key in ("delivery", "loyalty", "promotions"):
        info[key] = extra.get(key)

    return json.dumps(info, ensure_ascii=False, indent=2)