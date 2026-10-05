"""pytest plugin: drive TUIs with the same engine the MCP server uses — no LLM in the loop.

Usage (the plugin auto-registers via the `pytest11` entry point):

    def test_htop_shows_header(tui):
        s = tui.launch("htop", mode="buffer", dimensions=(120, 40))
        s.expect("CPU")
        s.assert_contains("Mem")
        assert s.cursor()[0] >= 0

Every session launched through the fixture is closed (and its process reaped)
at test teardown, pass or fail.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import pexpect
import pytest

from mcp_tui_test.core import ScreenSession, SessionRegistry, decode_keys


class TuiHandle:
    """Assertion-flavoured wrapper around ScreenSession for test code."""

    def __init__(self, session: ScreenSession):
        self.session = session

    # thin passthroughs
    def send(self, keys: str, raw: bool = False) -> None:
        self.session.send(keys if raw else decode_keys(keys))

    def send_ctrl(self, key: str) -> None:
        self.session.send(chr(ord(key.lower()) - ord("a") + 1))

    def screen(self) -> str:
        return self.session.screen_text()

    def line(self, row: int) -> str:
        return self.session.get_buffer_line(row)

    def cursor(self) -> Tuple[int, int]:
        return self.session.get_cursor_position()

    # pytest-native assertions
    def expect(self, pattern: str, timeout: int = 10) -> None:
        self.session.process.timeout = timeout
        index = self.session.process.expect([pattern, pexpect.TIMEOUT, pexpect.EOF])
        if self.session.mode == "buffer":
            self.session._update_buffer()
        if index != 0:
            reason = "timeout" if index == 1 else "EOF"
            raise AssertionError(f"expect({pattern!r}) failed: {reason} after {timeout}s\nscreen:\n{self.safe_screen()}")

    def assert_contains(self, text: str) -> None:
        out = self.screen()
        if text not in out:
            raise AssertionError(f"{text!r} not on screen\nscreen:\n{out}")

    def assert_at(self, text: str, row: int, col: int) -> None:
        actual = "".join(self.session.get_char_at(row, col + i) for i in range(len(text)))
        if actual.strip() != text.strip():
            raise AssertionError(f"expected {text!r} at ({row},{col}), found {actual.strip()!r}")

    def wait_until_contains(self, text: str, timeout: float = 10, interval: float = 0.25) -> None:
        """Poll the screen (not the stream) until `text` renders — for full TUIs."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if text in self.screen():
                return
            time.sleep(interval)
        raise AssertionError(f"{text!r} did not appear within {timeout}s\nscreen:\n{self.safe_screen()}")

    def safe_screen(self) -> str:
        try:
            return self.screen()
        except Exception as e:  # process already gone
            return f"(screen unavailable: {e})"


class TuiFactory:
    """The `tui` fixture object: launch sessions that are cleaned up at teardown."""

    def __init__(self, registry: SessionRegistry):
        self._registry = registry
        self._counter = 0

    def launch(
        self,
        command: str,
        mode: str = "stream",
        dimensions: Tuple[int, int] = (80, 24),
        timeout: int = 30,
        session_id: Optional[str] = None,
    ) -> TuiHandle:
        self._counter += 1
        sid = session_id or f"pytest-{self._counter}"
        return TuiHandle(
            self._registry.launch(command=command, session_id=sid, timeout=timeout, dimensions=dimensions, mode=mode)
        )


@pytest.fixture
def tui():
    """Launch and drive TUI sessions; everything is closed at teardown."""
    registry = SessionRegistry()
    try:
        yield TuiFactory(registry)
    finally:
        registry.close_all()
