# -*- coding: utf-8 -*-
"""check_config.py — валидация chains_config.json."""

import json
import socket
from combo_mcp.config import _load_config


def check_config():
    """Валидация конфига."""
    cfg = _load_config()
    chains = cfg.get("chains", {})

    issues = []
    valid_count = 0

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
