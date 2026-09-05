# -*- coding: utf-8 -*-
"""health_check.py — health_check(refresh): стабильность получения данных по сетям.

Для каждой КОМБО-сети (kind=combo): HTTP-доступность, размер/время ответа,
кол-во позиций, успешность парсинга (refresh=true — реальный прогон), вердикт:
healthy / degraded / unavailable. Магазины (kind=store) здесь не участвуют —
их живость проверяется через store_search/store_categories. Сети проверяются
параллельно (refresh).
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from combo_mcp.config import get_chain_meta, get_chain_class, get_combo_chain_ids
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable
from combo_mcp.http_client import get_session, DEFAULT_TIMEOUT
from combo_mcp.params import to_bool


def health_check(refresh=False):
    """Проверка стабильности получения данных с сайтов."""
    try:
        refresh = to_bool(refresh)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    meta = {c["id"]: c for c in get_chain_meta()}
    chain_ids = get_combo_chain_ids()

    if refresh:
        # Параллельно: сети независимы (свои сессии/кэш-файлы)
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {
                ex.submit(_check_chain, meta[cid], True): cid for cid in chain_ids
            }
            by_id = {}
            for fut in futures:
                entry = fut.result()
                by_id[entry["id"]] = entry
        results = [by_id[cid] for cid in chain_ids]
    else:
        results = [_check_chain(meta[cid], False) for cid in chain_ids]

    return json.dumps(results, ensure_ascii=False, indent=2)


def _check_chain(c, refresh):
    """Полная проверка одной сети (HTTP + парсинг/кэш)."""
    cid = c["id"]
    url = c.get("url", "")
    entry = {
        "id": cid,
        "name": c["name"],
        "url": url,
        "http_ok": False,
        "http_status": None,
        "response_size": 0,
        "response_time_ms": None,
        "parse_ok": False,
        "parse_error": None,
        "items_count": 0,
        "verdict": "unknown",
    }

    entry.update(_http_check(url, c))
    if refresh:
        parse_ok, error, items = _try_parse(cid)
    else:
        parse_ok, error, items = _cache_info(cid)
    entry["parse_ok"] = parse_ok
    entry["parse_error"] = error
    entry["items_count"] = len(items) if items else 0

    if not entry["http_ok"]:
        entry["verdict"] = "unavailable"
    elif entry["items_count"] == 0:
        entry["verdict"] = "degraded"
    else:
        entry["verdict"] = "healthy"
    return entry


def _http_check(url, chain_config):
    """Быстрая проверка доступности: статус, размер, время."""
    result = {
        "http_ok": False,
        "http_status": None,
        "response_size": 0,
        "response_time_ms": None,
    }
    if not url:
        return result
    try:
        session, timeout = get_session(chain_config)
        t0 = time.time()
        r = session.get(url, timeout=timeout, verify=False, allow_redirects=True)
        elapsed_ms = round((time.time() - t0) * 1000)
        result["http_status"] = r.status_code
        result["response_time_ms"] = elapsed_ms
        if r.status_code == 200:
            result["http_ok"] = True
            result["response_size"] = len(r.content)
    except Exception:
        pass
    return result


def _try_parse(chain_id):
    """Реальный парсинг сети. Возвращает (ok, error, items)."""
    try:
        chain_cls = get_chain_class(chain_id)
        if chain_cls is None:
            return False, "Не найден парсер", None
        instance = chain_cls()
        items = instance.parse()
        save_cache(chain_id, items)
        return True, None, items
    except ChainUnavailable as e:
        return False, str(e), None
    except Exception as e:
        return False, str(e), None


def _cache_info(chain_id):
    """Данные из кэша без обращения к сайту."""
    cache_data = load_cache(chain_id)
    if cache_data:
        items = cache_data.get("items", [])
        return True, None, items
    return False, "Нет кэша", None
