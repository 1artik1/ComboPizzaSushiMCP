# -*- coding: utf-8 -*-
"""ci_smoke.py — быстрый CI-смоук БЕЗ сети: сервер стартует, 13 инструментов
зарегистрированы, базовые инструменты отвечают валидным JSON.

Используется в .github/workflows/ci.yml (push). Полный прогон — nightly.yml.
"""

import asyncio
import json
import os
import subprocess
import sys

import mcp.client.stdio as stdio_client
from mcp.client.session import ClientSession

_project_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_project_dir)
SERVER_SCRIPT = os.path.join(_parent_dir, "combo_mcp", "server.py")
PYTHON = os.path.join(_parent_dir, ".venv", "Scripts", "python.exe")

EXPECTED_TOOLS = [
    "list_chains", "parse_menu", "best_combo", "compare", "status",
    "verify_chain", "check_price", "diff_menu", "check_config",
    "health_check", "chain_info", "help", "favorites",
]

QUICK_TOOLS = [
    ("list_chains", {}),
    ("status", {}),
    ("check_config", {}),
    ("help", {"action": ""}),
    ("favorites", {"action": "list"}),
]

_failures = []


async def run():
    proc = subprocess.Popen(
        [PYTHON, SERVER_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_parent_dir,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    try:
        async with stdio_client.stdio_client(
            stdio_client.StdioServerParameters(
                command=PYTHON,
                args=[SERVER_SCRIPT],
                cwd=_parent_dir,
                env={**os.environ, "PYTHONUTF8": "1"},
            )
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = sorted([t.name for t in tools.tools])
                missing = [n for n in EXPECTED_TOOLS if n not in tool_names]
                extra = [n for n in tool_names if n not in EXPECTED_TOOLS]
                if missing or extra:
                    _failures.append(f"tools: missing={missing} extra={extra}")
                else:
                    print(f"OK tools: {len(tool_names)} инструментов")

                for tool_name, args in QUICK_TOOLS:
                    resp = await session.call_tool(tool_name, args)
                    text = ""
                    for c in resp.content:
                        if hasattr(c, "text"):
                            text += c.text
                    try:
                        data = json.loads(text)
                        if not isinstance(data, (dict, list)):
                            raise ValueError("не dict/list")
                        print(f"OK {tool_name}: JSON")
                    except Exception as e:
                        _failures.append(f"{tool_name}: {e}: {text[:200]}")
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def main():
    asyncio.run(run())
    if _failures:
        print("FAIL:")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("CI SMOKE OK")


if __name__ == "__main__":
    main()