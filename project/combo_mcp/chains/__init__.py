# -*- coding: utf-8 -*-
"""chains package — авто-регистрация: импортирует все модули, собирает реестр."""

# Import base to register chains
from combo_mcp.chains.base import get_chain_class, _CHAIN_REGISTRY  # noqa: F401

# Import sub-modules to register their chains
from combo_mcp.chains import la_pizza  # noqa: F401
from combo_mcp.chains import sushi_darom  # noqa: F401
from combo_mcp.chains import anti_sushi  # noqa: F401
from combo_mcp.chains import sushi_time  # noqa: F401
from combo_mcp.chains import ninja_food  # noqa: F401
from combo_mcp.chains import pizza_kuba  # noqa: F401
from combo_mcp.chains import dodo  # noqa: F401
