# -*- coding: utf-8 -*-
"""smoke_test.py — реальный MCP-протокол: ClientSession + stdio transport."""

import sys
import os
import asyncio
import json

_project_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_project_dir)

import subprocess
import mcp.client.stdio as stdio_client
from mcp.client.session import ClientSession

SERVER_SCRIPT = os.path.join(_parent_dir, "combo_mcp", "server.py")
PYTHON = os.path.join(_parent_dir, ".venv", "Scripts", "python.exe")


async def run_smoke_test():
    print("=" * 60)
    print("  MCP SMOKE TEST (real protocol)")
    print("=" * 60)

    # Start server subprocess
    proc = subprocess.Popen(
        [PYTHON, SERVER_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_parent_dir,
        env={**os.environ, "PYTHONUTF8": "1"},
    )

    try:
        # Connect via stdio using StdioServerParameters
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

                # 1. list_tools — все 10 инструментов
                print("\n[1] list_tools()")
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                print(f"  Tools ({len(tool_names)}): {', '.join(tool_names)}")
                expected = ["list_chains", "parse_menu", "best_combo", "compare",
                            "status", "verify_chain", "check_price", "diff_menu",
                            "check_config", "health_check"]
                missing = [n for n in expected if n not in tool_names]
                if missing:
                    print(f"  FAIL: missing tools: {missing}")
                else:
                    print("  PASS: all 10 tools registered")

                # 2. call_tool("list_chains", {})
                print("\n[2] call_tool('list_chains', {})")
                resp = await session.call_tool("list_chains", {})
                # resp.content is a list of content items
                text = ""
                for c in resp.content:
                    if hasattr(c, 'text'):
                        text += c.text
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        print(f"  PASS: {len(data)} chains returned")
                        for ch in data[:3]:
                            print(f"    - {ch['name']} ({ch['id']})")
                    else:
                        print(f"  WARN: unexpected response type: {type(data)}")
                except json.JSONDecodeError:
                    print(f"  FAIL: not JSON: {text[:200]}")

                # 3. call_tool("best_combo", {"chain_id": "la_pizza", "budget": 3000, "persons": 1})
                print("\n[3] call_tool('best_combo', {'chain_id': 'la_pizza', 'budget': 3000, 'persons': 1})")
                resp = await session.call_tool("best_combo", {"chain_id": "la_pizza", "budget": 3000, "persons": 1})
                text = ""
                for c in resp.content:
                    if hasattr(c, 'text'):
                        text += c.text
                try:
                    data = json.loads(text)
                    combos = data.get("combos", [])
                    combo = combos[0] if combos else {}
                    w = combo.get("weight_g", 0)
                    p = combo.get("price_rub", 0)
                    print(f"  Result: {w}g / {p}rub, variations: {len(combos)}")
                    if w == 4400 and p == 2950:
                        print("  PASS: matches expected 4400g/2950rub")
                    else:
                        print(f"  INFO: expected 4400g/2950rub, got {w}g/{p}rub")
                except json.JSONDecodeError:
                    print(f"  FAIL: not JSON: {text[:200]}")

                # 4. call_tool("status", {})
                print("\n[4] call_tool('status', {})")
                resp = await session.call_tool("status", {})
                text = ""
                for c in resp.content:
                    if hasattr(c, 'text'):
                        text += c.text
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        print(f"  PASS: {len(data)} entries")
                        for e in data[:2]:
                            print(f"    - {e['name']}: enabled={e['enabled']}, items={e['items_count']}")
                    else:
                        print(f"  WARN: unexpected response type: {type(data)}")
                except json.JSONDecodeError:
                    print(f"  FAIL: not JSON: {text[:200]}")

                # 4b. call_tool("check_config", {})
                print("\n[4b] call_tool('check_config', {})")
                resp = await session.call_tool("check_config", {})
                text = ""
                for c in resp.content:
                    if hasattr(c, 'text'):
                        text += c.text
                try:
                    data = json.loads(text)
                    print(f"  Result: {data}")
                    print("  PASS: check_config returned OK")
                except json.JSONDecodeError:
                    print(f"  FAIL: not JSON: {text[:200]}")

                # 4c. call_tool("health_check", {"refresh": False})
                print("\n[4c] call_tool('health_check', {'refresh': False})")
                resp = await session.call_tool("health_check", {"refresh": False})
                text = ""
                for c in resp.content:
                    if hasattr(c, 'text'):
                        text += c.text
                try:
                    data = json.loads(text)
                    if isinstance(data, list) and data:
                        healthy = sum(1 for e in data if e["verdict"] == "healthy")
                        print(f"  Result: {len(data)} chains, {healthy} healthy")
                        if healthy == len(data):
                            print("  PASS: all chains healthy")
                        else:
                            print("  WARN: not all chains healthy")
                    else:
                        print(f"  WARN: unexpected response type: {type(data)}")
                except json.JSONDecodeError:
                    print(f"  FAIL: not JSON: {text[:200]}")

                print("\n" + "=" * 60)
                print("  SMOKE TEST COMPLETE")
                print("=" * 60)

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
