# -*- coding: utf-8 -*-
"""logs.py — логирование ошибок парсеров/тулов в logs/server.log.

Использование: log_error("fetch la_pizza", "ConnectionError: ...").
"""

import logging
import os

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_PATH = os.path.join(_LOG_DIR, "server.log")

_logger = None


def get_logger():
    """Логгер с файловым хендлером (инициализация один раз)."""
    global _logger
    if _logger is None:
        os.makedirs(_LOG_DIR, exist_ok=True)
        _logger = logging.getLogger("combo-engine")
        if not _logger.handlers:
            _logger.setLevel(logging.INFO)
            handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            _logger.addHandler(handler)
            _logger.propagate = False
    return _logger


def log_error(context, message):
    """Записать ошибку в лог: log_error("fetch la_pizza", "ConnectionError")"""
    get_logger().error("[%s] %s", context, message)