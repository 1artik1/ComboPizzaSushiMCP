# -*- coding: utf-8 -*-
"""check_config.py — валидация chains_config.json."""

import json
import socket
import re
from combo_mcp.config import _load_config


def check_config():
    """Валидация конфига."""
    cfg = _load_config()
    chains = cfg.get("chains", {})

    issues = []
    valid_count = 0

    # extra_refresh_at: "HH:MM"
    extra_refresh = cfg.get("extra_refresh_at", "11:00")
    if not (isinstance(extra_refresh, str)
            and re.fullmatch(r"[0-2]\d:[0-5]\d", extra_refresh)
            and int(extra_refresh[:2]) < 24):
        issues.append(
            f"extra_refresh_at: некорректный формат '{extra_refresh}' "
            "(ожидается 'HH:MM')"
        )

    required_fields = ["url"]

    for cid, cdata in chains.items():
        # Check required fields
        for field in required_fields:
            if field not in cdata:
                issues.append(f"{cid}: отсутствует '{field}'")
                continue

        # Check enabled
        enabled = cdata.get("enabled", True)

        # HEAD check URL
        url = cdata.get("url", "")
        url_ok = False
        if url:
            try:
                host = url.replace("https://", "").replace("http://", "").split("/")[0]
                port = 443 if url.startswith("https") else 80
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((host, port))
                s.close()
                url_ok = True
            except Exception:
                url_ok = False
                issues.append(f"{cid}: URL недоступен — {url}")

        if url_ok:
            valid_count += 1

    result = {
        "total_chains": len(chains),
        "valid_count": valid_count,
        "issues": issues,
    }

    if not issues:
        result["status"] = "конфиг в порядке"
    else:
        result["status"] = "есть проблемы"

    return json.dumps(result, ensure_ascii=False, indent=2)
