# -*- coding: utf-8 -*-
"""clear_cache.py — удаляет cache\*.json.

Запуск: python scripts\clear_cache.py
"""

import os
import sys

_project_dir = os.path.dirname(os.path.abspath(__file__))
_cache_dir = os.path.join(_project_dir, "..", "cache")

if os.path.exists(_cache_dir):
    count = 0
    for fn in os.listdir(_cache_dir):
        if fn.endswith(".json"):
            os.remove(os.path.join(_cache_dir, fn))
            count += 1
    print(f"Cache cleared: {count} files removed from {_cache_dir}")
else:
    print(f"Cache directory not found: {_cache_dir}")
