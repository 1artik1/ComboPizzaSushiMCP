# -*- coding: utf-8 -*-
"""shared.py — общие хелперы загрузки/фильтрации позиций для MCP-тулов.

fetch_items: кэш с TTL + stale-if-error (при неудачном парсинге — старый
кэш с флагом stale и причиной ошибки).
"""

import re

from combo_mcp.config import get_chain_class
from combo_mcp.cache import load_cache, load_items_with_ttl, save_cache
from combo_mcp.chains.base import ChainUnavailable
from combo_mcp.logs import log_error


def fetch_items(chain_id, refresh=False, allow_stale=True):
    """Загрузить позиции: кэш с TTL или свежий парсинг.

    Возвращает (items, stale, error):
      items — list позиций или None, если данных нет;
      stale — True, если отдан старый кэш после неудачного refresh;
      error — причина неудачи парсинга (str) или None.
    """
    if not refresh:
        items = load_items_with_ttl(chain_id)
        if items is not None:
            return items, False, None

    error = None
    try:
        chain_cls = get_chain_class(chain_id)
        if chain_cls is None:
            error = f"Не найден парсер для {chain_id}"
            log_error(f"fetch {chain_id}", error)
        else:
            items = chain_cls().parse()
            save_cache(chain_id, items)
            return items, False, None
    except ChainUnavailable as e:
        error = str(e)
        log_error(f"fetch {chain_id}", error)
    except Exception as e:
        error = str(e)
        log_error(f"fetch {chain_id}", error)

    if allow_stale:
        cache_data = load_cache(chain_id)
        if cache_data and cache_data.get("items"):
            return cache_data["items"], True, error
    return None, True, error


def split_items_str(items_str):
    """Разбить по запятым-разделителям вне скобок.

    'НАГГЕТСЫ (9 шт, 20 г/шт)' — одна часть (запятая внутри скобок).
    'Кола 0,33л г/л' — одна часть (запятая между цифрами — десятичная,
    не разделитель). Разделитель — запятая, за которой идёт пробел.
    """
    parts, depth, cur = [], 0, ""
    for i, ch in enumerate(items_str):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        nxt = items_str[i + 1] if i + 1 < len(items_str) else ""
        is_sep = ch == "," and depth == 0 and (nxt == " " or nxt == "")
        if is_sep:
            if cur.strip():
                parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def build_items_list(items_str, valid_items):
    """'Имя (500 г) x2, Имя x1' -> [{name, count, price_rub, weight_g, weight_source,
    category, group}, ...].

    Повторяющиеся имена (одинаковые товары по разным ценам) маппятся по очереди.
    При промо добавляются base_price_rub/discount_rub (из _base_price/_promo_discount).
    """
    by_name = {}
    for it in valid_items:
        by_name.setdefault(it["_local_name"], []).append(it)

    out = []
    for chunk in split_items_str(items_str):
        m = re.match(r"^(.*?)\s*x(\d+)$", chunk)
        name = re.sub(r"\s*\([^()]*\)\s*$", "", m.group(1).strip()) if m else chunk
        cnt = int(m.group(2)) if m else 1
        pool = by_name.get(name)
        it = pool.pop(0) if pool else None
        entry = {
            "name": name,
            "count": cnt,
            "price_rub": it["price_rub"] if it else None,
            "weight_g": it["weight_g"] if it else None,
            "weight_source": it.get("weight_source") if it else None,
            "category": it.get("category", "") if it else "",
            "group": it.get("_group", "") if it else "",
        }
        if it:
            if it.get("_base_price") is not None:
                entry["base_price_rub"] = it["_base_price"]
            if it.get("_promo_discount"):
                entry["discount_rub"] = it["_promo_discount"]
        out.append(entry)
    return out