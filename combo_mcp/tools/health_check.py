# -*- coding: utf-8 -*-
"""health_check.py — health_check(refresh): стабильность получения данных по сетям.

Для каждой сети: HTTP-доступность, размер/время ответа, кол-во позиций,
успешность парсинга (refresh=true — реальный прогон), вердикт:
healthy / degraded / unavailable.
"""

import json
import time
import socket
from combo_mcp.config import get_chain_meta, get_chain_class
from combo_mcp.cache import load_cache, save_cache
from combo_mcp.chains.base import ChainUnavailable
from combo_mcp.http_client import get_session, DEFAULT_TIMEOUT


def health_check(refresh=False):
    """Проверка стабильности получения данных с сайтов."""
    meta = get_chain_meta()
    results = []

    for c in meta:
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

        # --- HTTP check ---
        http_check = _http_check(url, c)
        entry.update(http_check)

        # --- Parse check ---
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

        results.append(entry)

    return json.dumps(results, ensure_ascii=False, indent=2)


def _http_check(url, chain_config):
    """Быстрая проверка доступности: статус, размер, время."""
    result = {"http_ok": False, "http_status": None,
              "response_size": 0, "response_time_ms": None}
    if not url:
        return result
    try:
        socket.setdefaulttimeout(DEFAULT_TIMEOUT)
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
    finally:
        socket.setdefaulttimeout(None)
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