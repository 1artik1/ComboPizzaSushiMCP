# -*- coding: utf-8 -*-
"""tools package — авто-регистрация инструментов по декоратору."""

# Import base to get registry
from combo_mcp.tools.base import get_tools  # noqa: F401

# Import sub-modules to register their chain parsers
from combo_mcp.tools import list_chains  # noqa: F401
from combo_mcp.tools import parse_menu  # noqa: F401
from combo_mcp.tools import best_combo  # noqa: F401
from combo_mcp.tools import compare  # noqa: F401
from combo_mcp.tools import status  # noqa: F401
from combo_mcp.tools import verify_chain  # noqa: F401
from combo_mcp.tools import check_price  # noqa: F401
from combo_mcp.tools import diff_menu  # noqa: F401
from combo_mcp.tools import check_config  # noqa: F401
