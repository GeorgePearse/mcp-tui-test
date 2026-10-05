"""MCP server for TUI testing — structured outputs over the core session engine.

Every tool returns a TypedDict (FastMCP derives an output schema from it and ships
`structuredContent` alongside readable text), so agents branch on `success`/fields
instead of parsing prose. The current screen is also exposed as an MCP resource at
`tui://{session_id}/screen`.
"""

from __future__ import annotations

import pexpect
from typing import Any, List, Optional, TypedDict

try:  # mcp >= 2.0 renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as _Server
except ModuleNotFoundError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from mcp_tui_test.core import (
    SessionNotFoundError,
    SessionRegistry,
    decode_keys,
)

mcp = _Server("tui-test")
registry = SessionRegistry()


# ---- result shapes ---------------------------------------------------------
class LaunchResult(TypedDict):
    success: bool
    session_id: str
    command: str
    width: int
    height: int
    mode: str
    error: Optional[str]


class ActionResult(TypedDict):
    success: bool
    session_id: str
    error: Optional[str]


class ScreenResult(TypedDict):
    success: bool
    session_id: str
    mode: str
    screen: str
    error: Optional[str]


class ExpectResult(TypedDict):
    success: bool
    session_id: str
    pattern: str
    outcome: str  # "found" | "timeout" | "eof" | "error"
    error: Optional[str]


class AssertResult(TypedDict):
    success: bool
    passed: bool
    session_id: str
    expected: str
    found: Optional[str]
    screen_excerpt: Optional[str]
    error: Optional[str]


class CursorResult(TypedDict):
    success: bool
    session_id: str
    row: int
    col: int
    error: Optional[str]


class RegionResult(TypedDict):
    success: bool
    session_id: str
    text: str
    error: Optional[str]


class SessionInfo(TypedDict):
    session_id: str
    mode: str
    command: str
    alive: bool


class SessionList(TypedDict):
    success: bool
    sessions: List[SessionInfo]
    reaped: dict


def _err(shape: Any, session_id: str, error: str, **extra: Any) -> Any:
    base = {k: v for k, v in extra.items()}
    base.update({"success": False, "session_id": session_id, "error": error})
    return base


# ---- tools -----------------------------------------------------------------
@mcp.tool()
def launch_tui(
    command: str,
    session_id: str = "default",
    timeout: int = 30,
    dimensions: str = "80x24",
    mode: str = "stream",
) -> LaunchResult:
    """Launch a TUI application for testing.

    Args:
        command: The command to launch.
        session_id: Unique identifier for this session.
        timeout: Default pexpect timeout in seconds.
        dimensions: Terminal dimensions as WIDTHxHEIGHT.
        mode: "stream" for CLI tools, "buffer" for full TUIs (position/cursor aware).
    """
    try:
        width, height = map(int, dimensions.lower().split("x"))
        registry.launch(
            command=command, session_id=session_id, timeout=timeout, dimensions=(width, height), mode=mode
        )
        return LaunchResult(
            success=True, session_id=session_id, command=command, width=width, height=height, mode=mode, error=None
        )
    except Exception as e:
        return LaunchResult(
            success=False, session_id=session_id, command=command, width=0, height=0, mode=mode, error=str(e)
        )


@mcp.tool()
def send_keys(keys: str, session_id: str = "default", delay: float = 0.1, raw: bool = False) -> ActionResult:
    """Send keyboard input. Escapes like \\n, \\t, \\x1b are decoded unless raw=True."""
    try:
        session = registry.get(session_id)
        session.send(keys if raw else decode_keys(keys))
        if delay > 0.1:
            import time

            time.sleep(delay - 0.1)
        return ActionResult(success=True, session_id=session_id, error=None)
    except SessionNotFoundError:
        return ActionResult(success=False, session_id=session_id, error=f"no active session: {session_id}")
    except Exception as e:
        return ActionResult(success=False, session_id=session_id, error=str(e))


@mcp.tool()
def send_ctrl(key: str, session_id: str = "default") -> ActionResult:
    """Send a Ctrl+<key> combination (e.g. key='c' sends Ctrl-C)."""
    try:
        session = registry.get(session_id)
        session.send(chr(ord(key.lower()) - ord("a") + 1))
        return ActionResult(success=True, session_id=session_id, error=None)
    except SessionNotFoundError:
        return ActionResult(success=False, session_id=session_id, error=f"no active session: {session_id}")
    except Exception as e:
        return ActionResult(success=False, session_id=session_id, error=str(e))


@mcp.tool()
def capture_screen(
    session_id: str = "default", include_ansi: bool = False, use_buffer: Optional[bool] = None
) -> ScreenResult:
    """Capture the current screen (buffer display in buffer mode, cleaned stream otherwise)."""
    try:
        session = registry.get(session_id)
        if use_buffer is None:
            use_buffer = session.mode == "buffer"
        if use_buffer and session.mode == "buffer":
            return ScreenResult(
                success=True, session_id=session_id, mode="buffer", screen=session.get_buffer_display(), error=None
            )
        return ScreenResult(
            success=True,
            session_id=session_id,
            mode="stream",
            screen=session.get_stream_output(include_ansi=include_ansi),
            error=None,
        )
    except SessionNotFoundError:
        return ScreenResult(success=False, session_id=session_id, mode="", screen="", error=f"no active session: {session_id}")
    except Exception as e:
        return ScreenResult(success=False, session_id=session_id, mode="", screen="", error=str(e))


@mcp.tool()
def expect_text(pattern: str, session_id: str = "default", timeout: int = 10) -> ExpectResult:
    """Wait until a regex/text pattern appears in the output (or timeout/EOF)."""
    try:
        session = registry.get(session_id)
        session.process.timeout = timeout
        index = session.process.expect([pattern, pexpect.TIMEOUT, pexpect.EOF])
        if session.mode == "buffer":
            session._update_buffer()
        outcome = ["found", "timeout", "eof"][index]
        return ExpectResult(success=outcome == "found", session_id=session_id, pattern=pattern, outcome=outcome, error=None)
    except SessionNotFoundError:
        return ExpectResult(
            success=False, session_id=session_id, pattern=pattern, outcome="error", error=f"no active session: {session_id}"
        )
    except Exception as e:
        return ExpectResult(success=False, session_id=session_id, pattern=pattern, outcome="error", error=str(e))


@mcp.tool()
def assert_contains(text: str, session_id: str = "default", use_buffer: Optional[bool] = None) -> AssertResult:
    """Assert the current screen contains `text`; on failure includes a screen excerpt."""
    try:
        session = registry.get(session_id)
        if use_buffer is None:
            use_buffer = session.mode == "buffer"
        output = session.get_buffer_display() if (use_buffer and session.mode == "buffer") else session.get_stream_output()
        passed = text in output
        return AssertResult(
            success=True,
            passed=passed,
            session_id=session_id,
            expected=text,
            found=text if passed else None,
            screen_excerpt=None if passed else output[-800:],
            error=None,
        )
    except SessionNotFoundError:
        return AssertResult(
            success=False, passed=False, session_id=session_id, expected=text, found=None, screen_excerpt=None,
            error=f"no active session: {session_id}",
        )
    except Exception as e:
        return AssertResult(
            success=False, passed=False, session_id=session_id, expected=text, found=None, screen_excerpt=None, error=str(e)
        )


@mcp.tool()
def assert_at_position(text: str, row: int, col: int, session_id: str = "default") -> AssertResult:
    """Assert `text` appears at (row, col) — buffer mode only."""
    try:
        session = registry.get(session_id)
        actual = "".join(session.get_char_at(row, col + i) for i in range(len(text)))
        passed = actual.strip() == text.strip()
        return AssertResult(
            success=True, passed=passed, session_id=session_id, expected=text,
            found=actual.strip(), screen_excerpt=None, error=None,
        )
    except SessionNotFoundError:
        return AssertResult(
            success=False, passed=False, session_id=session_id, expected=text, found=None, screen_excerpt=None,
            error=f"no active session: {session_id}",
        )
    except Exception as e:
        return AssertResult(
            success=False, passed=False, session_id=session_id, expected=text, found=None, screen_excerpt=None, error=str(e)
        )


@mcp.tool()
def get_cursor_position(session_id: str = "default") -> CursorResult:
    """Current cursor (row, col) — buffer mode only."""
    try:
        row, col = registry.get(session_id).get_cursor_position()
        return CursorResult(success=True, session_id=session_id, row=row, col=col, error=None)
    except SessionNotFoundError:
        return CursorResult(success=False, session_id=session_id, row=-1, col=-1, error=f"no active session: {session_id}")
    except Exception as e:
        return CursorResult(success=False, session_id=session_id, row=-1, col=-1, error=str(e))


@mcp.tool()
def get_screen_region(
    row_start: int, row_end: int, col_start: int = 0, col_end: Optional[int] = None, session_id: str = "default"
) -> RegionResult:
    """Extract a rectangular screen region — buffer mode only."""
    try:
        session = registry.get(session_id)
        if col_end is None:
            col_end = session.dimensions[0]
        lines = [session.get_buffer_line(r)[col_start:col_end] for r in range(row_start, row_end)]
        return RegionResult(success=True, session_id=session_id, text="\n".join(lines), error=None)
    except SessionNotFoundError:
        return RegionResult(success=False, session_id=session_id, text="", error=f"no active session: {session_id}")
    except Exception as e:
        return RegionResult(success=False, session_id=session_id, text="", error=str(e))


@mcp.tool()
def get_line(row: int, session_id: str = "default") -> RegionResult:
    """Get one screen-buffer line — buffer mode only."""
    try:
        return RegionResult(success=True, session_id=session_id, text=registry.get(session_id).get_buffer_line(row), error=None)
    except SessionNotFoundError:
        return RegionResult(success=False, session_id=session_id, text="", error=f"no active session: {session_id}")
    except Exception as e:
        return RegionResult(success=False, session_id=session_id, text="", error=str(e))


@mcp.tool()
def close_session(session_id: str = "default") -> ActionResult:
    """Close a session and reap its process."""
    try:
        registry.get(session_id)
        registry.close(session_id)
        return ActionResult(success=True, session_id=session_id, error=None)
    except SessionNotFoundError:
        return ActionResult(success=False, session_id=session_id, error=f"no active session: {session_id}")


@mcp.tool()
def list_sessions() -> SessionList:
    """List active sessions (dead/expired ones are reaped and reported)."""
    reaped = registry.reap()
    return SessionList(
        success=True,
        sessions=[
            SessionInfo(session_id=sid, mode=s.mode, command=s.command, alive=s.is_alive())
            for sid, s in registry.sessions.items()
        ],
        reaped=reaped,
    )


# ---- resources --------------------------------------------------------------
@mcp.resource("tui://{session_id}/screen")
def screen_resource(session_id: str) -> str:
    """The session's current screen as plain text."""
    try:
        return registry.get(session_id).screen_text()
    except SessionNotFoundError:
        return f"(no active session: {session_id})"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
