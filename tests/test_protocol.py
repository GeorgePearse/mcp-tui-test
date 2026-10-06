"""Exercise the published contract over MCP stdio, for either implementation.

Set MCP_TUI_TEST_BINARY to also run these checks against a compiled Go server.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import jsonschema
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
SERVERS = [pytest.param(sys.executable, [str(ROOT / "server.py")], id="python")]
if os.environ.get("MCP_TUI_TEST_BINARY"):
    SERVERS.append(pytest.param(os.environ["MCP_TUI_TEST_BINARY"], [], id="go"))

FIELDS = {
    "launch_tui": {"success", "session_id", "command", "width", "height", "mode", "error"},
    "send_keys": {"success", "session_id", "error"},
    "send_ctrl": {"success", "session_id", "error"},
    "capture_screen": {"success", "session_id", "mode", "screen", "error"},
    "expect_text": {"success", "session_id", "pattern", "outcome", "error"},
    "assert_contains": {"success", "passed", "session_id", "expected", "found", "screen_excerpt", "error"},
    "assert_at_position": {"success", "passed", "session_id", "expected", "found", "screen_excerpt", "error"},
    "get_cursor_position": {"success", "session_id", "row", "col", "error"},
    "get_screen_region": {"success", "session_id", "text", "error"},
    "get_line": {"success", "session_id", "text", "error"},
    "close_session": {"success", "session_id", "error"},
    "list_sessions": {"success", "sessions", "reaped"},
}


@pytest.mark.parametrize("command,args", SERVERS)
def test_stdio_result_contract(command, args):
    async def exercise():
        params = StdioServerParameters(command=command, args=args)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                listed = (await client.list_tools()).model_dump(by_alias=True)
                schemas = {tool["name"]: tool["outputSchema"] for tool in listed["tools"]}
                assert set(schemas) == set(FIELDS)
                for name, fields in FIELDS.items():
                    assert set(schemas[name]["required"]) == fields, name

                async def call(name, **arguments):
                    result = (await client.call_tool(name, arguments)).model_dump(by_alias=True)
                    assert not result.get("isError"), result
                    data = result["structuredContent"]
                    assert set(data) == FIELDS[name], (name, data)
                    jsonschema.validate(data, schemas[name])
                    # Compatibility text must carry the same data, not a second contract.
                    text = "".join(c["text"] for c in result["content"] if c["type"] == "text")
                    assert json.loads(text) == data
                    return data

                assert await call("list_sessions") == {"success": True, "sessions": [], "reaped": {}}
                missing_calls = {
                    "send_keys": {"keys": "x"},
                    "send_ctrl": {"key": "c"},
                    "capture_screen": {},
                    "expect_text": {"pattern": "READY"},
                    "assert_contains": {"text": "READY"},
                    "assert_at_position": {"text": "READY", "row": 0, "col": 0},
                    "get_cursor_position": {},
                    "get_screen_region": {"row_start": 0, "row_end": 1},
                    "get_line": {"row": 0},
                    "close_session": {},
                }
                for name, arguments in missing_calls.items():
                    data = await call(name, session_id="absent", **arguments)
                    assert data["success"] is False
                    assert "no active session" in data["error"]
                    if "found" in data:
                        assert data["found"] is None and data["screen_excerpt"] is None

                invalid = await call("launch_tui", command="unused", dimensions="invalid")
                assert invalid["success"] is False and invalid["error"]

                # Hold the process open so lifecycle reaping cannot hide its final output.
                launch = await call("launch_tui", command="/bin/sh -c 'printf READY; read answer; printf DONE; read finish'",
                                    session_id="contract")
                assert launch["success"] is True and launch["error"] is None
                try:
                    sessions = await call("list_sessions")
                    assert len(sessions["sessions"]) == 1 and sessions["reaped"] == {}
                    matched = await call("expect_text", pattern="READY", session_id="contract", timeout=3)
                    assert matched["success"] and matched["outcome"] == "found" and matched["error"] is None
                    screen = await call("capture_screen", session_id="contract")
                    assert screen["success"] and "READY" in screen["screen"] and screen["error"] is None
                    passed = await call("assert_contains", text="READY", session_id="contract")
                    assert passed["success"] and passed["passed"] and passed["found"] == "READY"
                    assert passed["screen_excerpt"] is None and passed["error"] is None
                    failed = await call("assert_contains", text="missing", session_id="contract")
                    assert failed["success"] and not failed["passed"] and failed["found"] is None
                    assert "READY" in failed["screen_excerpt"] and failed["error"] is None
                    empty = await call("assert_contains", text="", session_id="contract")
                    assert empty["passed"] and empty["found"] == ""  # empty is not null
                    sent = await call("send_keys", keys="answer\n", raw=True, session_id="contract")
                    assert sent["success"] and sent["error"] is None
                    done = await call("expect_text", pattern="DONE", session_id="contract", timeout=3)
                    assert done["success"] and done["outcome"] == "found"
                finally:
                    closed = await call("close_session", session_id="contract")
                    assert closed["success"] and closed["error"] is None
                assert (await call("list_sessions"))["sessions"] == []

    asyncio.run(asyncio.wait_for(exercise(), timeout=60))
