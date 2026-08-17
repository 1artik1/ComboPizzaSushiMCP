# -*- coding: utf-8 -*-
"""chains package — авто-регистрация парсеров через pkgutil.

Импортирует все модули из combo_mcp.chains, пропускает "_*" и extra_utils,
ловит ошибки импорта и печатает предупреждение.
"""

import pkgutil
import sys

# Import base to register the registry and get_chain_class
from combo_mcp.chains.base import get_chain_class, _CHAIN_REGISTRY  # noqa: F401

# Auto-discover and import all chain modules
_loader = __loader__
if _loader is not None:
    _package_path = __path__
else:
    import os
    _package_path = [os.path.dirname(__file__)]

for importer, name, is_pkg in pkgutil.iter_modules(_package_path):
    # Пропуска private модули (_*) и extra_utils
    if name.startswith("_"):
        continue
    if name == "extra_utils":
        continue
    try:
        __import__(f"combo_mcp.chains.{name}")
    except Exception as e:
        print(f"[chains] пропущен модуль {name}: {e}")
