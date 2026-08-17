# -*- coding: utf-8 -*-
"""extra_cache.py — кэш доп. информации (доставка/акции/лояльность).

Срез: cache/extra_<chain>.json = {fetched_at, extra, last_error, stale}.
Обновление — раз в день в момент extra_refresh_at (см. config.get_extra_refresh_at);
если время ещё не наступило — отдаём срез без обращений к сети (ленивый механизм).
При ошибке парсинга — stale-if-error: старый срез + пометка.
"""

import json
import os
import time
import datetime

from combo_mcp import config as mcp_config
from combo_mcp.cache import _CACHE_DIR
from combo_mcp.chains.base import ChainUnavailable

_EXTRA_DIR = _CACHE_DIR


def _extra_path(chain_id):
    return os.path.join(_EXTRA_DIR, f"extra_{chain_id}.json")


def load_extra_cache(chain_id):
    """Прочитать срез. Returns dict or None."""
    path = _extra_path(chain_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return None


def _save_extra_cache(chain_id, extra, error=None, stale=False):
    os.makedirs(_EXTRA_DIR, exist_ok=True)
    data = {
        "fetched_at": time.time(),
        "extra": extra,
        "last_error": error,
        "stale": stale,
    }
    with open(_extra_path(chain_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _now_local():
    return datetime.datetime.now()


def _is_past_refresh(now, refresh_at):
    """Наступил ли сегодня момент обновления 'HH:MM'."""
    hh, mm = refresh_at.split(":")
    moment = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    return now >= moment


def _refresh_threshold(refresh_at):
    """Время, с которого срез считается устаревшим: вчера HH:MM (сегодня, если HH:MM уже прошло)."""
    now = _now_local()
    hh, mm = refresh_at.split(":")
    today = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    if now >= today:
        return today - datetime.timedelta(days=1)
    return today


def should_refresh(chain_id):
    """Нужно ли перепарсить доп. данные прямо сейчас.

    Логика: обновляемся раз в день в HH:MM (extra_refresh_at). Первый вызов после
    HH:MM в день, когда срез ещё не собирался, — обновляем; до HH:MM — отдаём срез.
    """
    cache_data = load_extra_cache(chain_id)
    if cache_data is None:
        return True
    threshold = _refresh_threshold(mcp_config.get_extra_refresh_at())
    return cache_data.get("fetched_at", 0) < threshold.timestamp()


def get_extra(chain_id, refresh=False):
    """Доп. информация сети: срез из кэша с ленивым обновлением.

    refresh=True — принудительно перепарсить. Возвращает dict:
    {extra, fetched_at, source_state, last_error, updated}.
    """
    need = refresh or should_refresh(chain_id)
    if not need:
        data = load_extra_cache(chain_id)
        return {
            "extra": data.get("extra"),
            "fetched_at": data.get("fetched_at"),
            "source_state": "snapshot",
            "last_error": data.get("last_error"),
            "updated": False,
        }

    error = None
    extra = None
    stale = False
    try:
        chain_cls = mcp_config.get_chain_class(chain_id)
        instance = chain_cls()
        extra = instance.parse_extra()
    except ChainUnavailable as e:
        error = str(e)
    except Exception as e:
        error = str(e)

    if extra is None:
        old = load_extra_cache(chain_id)
        if old and old.get("extra"):
            stale = True
            data = _save_extra_cache(chain_id, old["extra"], error=error, stale=True)
            return {
                "extra": old["extra"],
                "fetched_at": old.get("fetched_at"),
                "source_state": "stale",
                "last_error": error,
                "updated": False,
            }
        return {
            "extra": None,
            "fetched_at": None,
            "source_state": "error",
            "last_error": error or "Доп. данные недоступны",
            "updated": False,
        }

    data = _save_extra_cache(chain_id, extra, error=None, stale=False)
    return {
        "extra": extra,
        "fetched_at": data["fetched_at"],
        "source_state": "fresh",
        "last_error": None,
        "updated": True,
    }