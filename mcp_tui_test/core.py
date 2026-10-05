"""Session primitives for TUI testing — no MCP dependency.

This module is the engine shared by the MCP server (`mcp_tui_test.server`) and the
pytest plugin (`mcp_tui_test.pytest_plugin`): pexpect drives the process, pyte
optionally emulates the screen buffer, and SessionRegistry owns lifecycle —
caps, deadlines, dead-process reaping, and close-all on exit.
"""

from __future__ import annotations

import atexit
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import pexpect
import pyte

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

DEFAULT_MAX_SESSIONS = int(os.environ.get("MCP_TUI_MAX_SESSIONS", "8"))
DEFAULT_SESSION_TTL_S = float(os.environ.get("MCP_TUI_SESSION_TTL_S", "900"))


class SessionLimitError(RuntimeError):
    """Raised when launching would exceed the registry's session cap."""


class SessionNotFoundError(KeyError):
    """Raised when a session id has no live session."""


def decode_keys(keys: str) -> str:
    """Decode backslash escapes (\\n, \\t, \\x1b) without mangling non-ASCII input.

    A bare `codecs.decode(keys, "unicode_escape")` corrupts anything outside
    latin-1; round-tripping with backslashreplace keeps real unicode intact while
    still honouring literal escape sequences.
    """
    if "\\" not in keys:
        return keys
    return keys.encode("latin-1", "backslashreplace").decode("unicode_escape")


class ScreenSession:
    """A pexpect-driven process with optional pyte screen-buffer emulation."""

    def __init__(
        self,
        command: str,
        timeout: int = 30,
        dimensions: Tuple[int, int] = (80, 24),
        mode: str = "stream",
        ttl_s: float = DEFAULT_SESSION_TTL_S,
    ):
        if mode not in ("stream", "buffer"):
            raise ValueError(f"mode must be 'stream' or 'buffer', got {mode!r}")
        self.mode = mode
        self.dimensions = dimensions
        self.command = command
        self.created_at = time.monotonic()
        self.deadline = self.created_at + ttl_s if ttl_s > 0 else None
        width, height = dimensions

        self.process = pexpect.spawn(
            command,
            timeout=timeout,
            dimensions=(height, width),
            encoding="utf-8",
            codec_errors="replace",
        )

        self.screen: Optional[pyte.Screen] = None
        self.stream: Optional[pyte.Stream] = None
        if mode == "buffer":
            self.screen = pyte.Screen(width, height)
            self.stream = pyte.Stream(self.screen)
            self._update_buffer()

    # -- liveness -----------------------------------------------------------
    def is_alive(self) -> bool:
        try:
            return bool(self.process.isalive())
        except Exception:
            return False

    def expired(self) -> bool:
        return self.deadline is not None and time.monotonic() > self.deadline

    # -- io -----------------------------------------------------------------
    def _update_buffer(self) -> None:
        if self.mode != "buffer" or self.stream is None:
            return
        try:
            output = self.process.read_nonblocking(size=65536, timeout=0.1)
            if output:
                self.stream.feed(output)
        except (pexpect.TIMEOUT, pexpect.EOF):
            pass

    def send(self, keys: str) -> None:
        self.process.send(keys)
        time.sleep(0.1)
        if self.mode == "buffer":
            self._update_buffer()

    def get_stream_output(self, include_ansi: bool = False) -> str:
        output = self.process.before or ""
        # `after` holds the text a successful expect() matched; without it, the
        # natural "expect(X) then assert X on screen" sequence always failed.
        if isinstance(self.process.after, str):
            output += self.process.after
        if not include_ansi:
            output = ANSI_ESCAPE.sub("", output)
        return output

    def get_buffer_display(self) -> str:
        if self.mode != "buffer" or self.screen is None:
            raise RuntimeError("buffer mode not enabled for this session")
        self._update_buffer()
        return "\n".join(line.rstrip() for line in self.screen.display)

    def get_buffer_line(self, row: int) -> str:
        if self.mode != "buffer" or self.screen is None:
            raise RuntimeError("buffer mode not enabled for this session")
        self._update_buffer()
        if 0 <= row < self.screen.lines:
            return "".join(
                (self.screen.buffer[row].get(col).data if self.screen.buffer[row].get(col) else " ")
                for col in range(self.screen.columns)
            ).rstrip()
        return ""

    def get_cursor_position(self) -> Tuple[int, int]:
        if self.mode != "buffer" or self.screen is None:
            raise RuntimeError("buffer mode not enabled for this session")
        self._update_buffer()
        return (self.screen.cursor.y, self.screen.cursor.x)

    def get_char_at(self, row: int, col: int) -> str:
        if self.mode != "buffer" or self.screen is None:
            raise RuntimeError("buffer mode not enabled for this session")
        self._update_buffer()
        if 0 <= row < self.screen.lines and 0 <= col < self.screen.columns:
            char = self.screen.buffer[row].get(col)
            return char.data if char else " "
        return ""

    def screen_text(self) -> str:
        """Best-available textual screen: buffer display, else cleaned stream tail."""
        if self.mode == "buffer":
            return self.get_buffer_display()
        return self.get_stream_output(include_ansi=False)

    def close(self) -> None:
        """Close and reap the child; escalate to SIGKILL rather than leak it."""
        try:
            self.process.close(force=True)
        except Exception:
            try:
                self.process.terminate(force=True)
            except Exception:
                pass


@dataclass
class SessionRegistry:
    """Owns sessions: cap, TTL reaping, dead-process reaping, close-all."""

    max_sessions: int = DEFAULT_MAX_SESSIONS
    ttl_s: float = DEFAULT_SESSION_TTL_S
    sessions: Dict[str, ScreenSession] = field(default_factory=dict)

    def __post_init__(self) -> None:
        atexit.register(self.close_all)

    def reap(self) -> Dict[str, str]:
        """Remove dead or expired sessions; returns {session_id: reason}."""
        reaped: Dict[str, str] = {}
        for sid in list(self.sessions):
            s = self.sessions[sid]
            if not s.is_alive():
                reason = "process exited"
            elif s.expired():
                reason = "session TTL expired"
            else:
                continue
            s.close()
            del self.sessions[sid]
            reaped[sid] = reason
        return reaped

    def launch(
        self,
        command: str,
        session_id: str = "default",
        timeout: int = 30,
        dimensions: Tuple[int, int] = (80, 24),
        mode: str = "stream",
    ) -> ScreenSession:
        self.reap()
        if session_id in self.sessions:
            self.close(session_id)
        if len(self.sessions) >= self.max_sessions:
            raise SessionLimitError(
                f"session cap reached ({self.max_sessions}); close a session or raise MCP_TUI_MAX_SESSIONS"
            )
        session = ScreenSession(
            command=command, timeout=timeout, dimensions=dimensions, mode=mode, ttl_s=self.ttl_s
        )
        self.sessions[session_id] = session
        time.sleep(0.5)  # settle before first capture
        return session

    def get(self, session_id: str) -> ScreenSession:
        self.reap()
        if session_id not in self.sessions:
            raise SessionNotFoundError(session_id)
        return self.sessions[session_id]

    def close(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].close()
            del self.sessions[session_id]

    def close_all(self) -> None:
        for sid in list(self.sessions):
            self.close(sid)
