"""Tool-layer tests: structured results and the screen resource."""

import sys

from mcp_tui_test import server

PY = sys.executable


def setup_function(_):
    server.registry.close_all()


def teardown_function(_):
    server.registry.close_all()


def test_launch_and_capture_structured():
    res = server.launch_tui(f'{PY} -c "print(\'READY\'); input()"', session_id="t1", timeout=5)
    assert res["success"] is True
    assert (res["width"], res["height"]) == (80, 24)

    exp = server.expect_text("READY", session_id="t1", timeout=5)
    assert exp["success"] is True and exp["outcome"] == "found"

    cap = server.capture_screen(session_id="t1")
    assert cap["success"] is True and cap["mode"] == "stream"


def test_missing_session_is_structured_error():
    res = server.send_keys("x", session_id="nope")
    assert res["success"] is False
    assert "no active session" in res["error"]


def test_assert_contains_failure_includes_excerpt():
    server.launch_tui(f'{PY} -c "print(\'alpha beta\'); input()"', session_id="t2", timeout=5)
    server.expect_text("beta", session_id="t2", timeout=5)
    res = server.assert_contains("gamma", session_id="t2")
    assert res["success"] is True and res["passed"] is False
    assert res["screen_excerpt"] is not None


def test_buffer_position_assert():
    cmd = f"{PY} -c \"import sys; sys.stdout.write('\\x1b[2J\\x1b[1;1HOK'); sys.stdout.flush(); input()\""
    server.launch_tui(cmd, session_id="t3", timeout=5, dimensions="40x10", mode="buffer")
    import time

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        res = server.assert_at_position("OK", 0, 0, session_id="t3")
        if res["passed"]:
            break
        time.sleep(0.1)
    assert res["passed"] is True, res

    cur = server.get_cursor_position(session_id="t3")
    assert cur["success"] is True and cur["row"] >= 0


def test_list_sessions_reports_reaped():
    server.launch_tui(f'{PY} -c "pass"', session_id="dies", timeout=5)
    import time

    time.sleep(0.8)  # let it exit
    listed = server.list_sessions()
    assert listed["success"] is True
    assert "dies" in listed["reaped"] or all(s["session_id"] != "dies" for s in listed["sessions"])


def test_screen_resource():
    server.launch_tui(f'{PY} -c "print(\'RESOURCE_TEXT\'); input()"', session_id="r1", timeout=5)
    server.expect_text("RESOURCE_TEXT", session_id="r1", timeout=5)
    text = server.screen_resource("r1")
    assert isinstance(text, str)
    missing = server.screen_resource("absent")
    assert "no active session" in missing


def test_tools_have_output_schemas():
    import asyncio

    tools = asyncio.run(server.mcp.list_tools())
    by_name = {t.name: t for t in tools}
    assert "launch_tui" in by_name
    tool = by_name["launch_tui"]
    schema = getattr(tool, "output_schema", None) or getattr(tool, "outputSchema", None)
    assert schema is not None and "success" in schema.get("properties", {})
