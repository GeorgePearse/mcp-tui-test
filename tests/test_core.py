"""Core engine tests: sessions, registry caps, reaping, key decoding."""

import sys
import time

import pytest

from mcp_tui_test.core import (
    ScreenSession,
    SessionLimitError,
    SessionNotFoundError,
    SessionRegistry,
    decode_keys,
)

PY = sys.executable


def test_decode_keys_escapes_and_unicode():
    assert decode_keys("hello\\n") == "hello\n"
    assert decode_keys("\\x1b[A") == "\x1b[A"
    assert decode_keys("naïve ✓") == "naïve ✓"  # unicode survives
    assert decode_keys("mixed ✓\\t") == "mixed ✓\t"


def test_stream_session_echo():
    s = ScreenSession(f'{PY} -c "print(input())"', timeout=5)
    try:
        s.send("hello world\n")
        s.process.expect("hello world")
    finally:
        s.close()
    assert not s.is_alive()


def test_buffer_session_display_and_cursor():
    s = ScreenSession(
        f"{PY} -c \"import sys; sys.stdout.write('\\x1b[2J\\x1b[3;5HMARK'); sys.stdout.flush(); input()\"",
        timeout=5,
        dimensions=(40, 10),
        mode="buffer",
    )
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and "MARK" not in s.get_buffer_display():
            time.sleep(0.1)
        display = s.get_buffer_display()
        assert "MARK" in display
        # row 2 (0-indexed), col 4
        assert s.get_char_at(2, 4) == "M"
        assert s.get_buffer_line(2).strip() == "MARK"
    finally:
        s.close()


def test_registry_cap_and_reap_dead():
    reg = SessionRegistry(max_sessions=2, ttl_s=0)
    try:
        reg.launch(f'{PY} -c "input()"', session_id="a", timeout=5)
        reg.launch(f'{PY} -c "input()"', session_id="b", timeout=5)
        with pytest.raises(SessionLimitError):
            reg.launch(f'{PY} -c "input()"', session_id="c", timeout=5)
        # kill one; the registry should reap it and admit a new session
        reg.sessions["a"].process.terminate(force=True)
        time.sleep(0.3)
        reaped = reg.reap()
        assert "a" in reaped
        reg.launch(f'{PY} -c "input()"', session_id="c", timeout=5)
        assert set(reg.sessions) == {"b", "c"}
    finally:
        reg.close_all()
    assert reg.sessions == {}


def test_registry_ttl_expiry():
    reg = SessionRegistry(max_sessions=4, ttl_s=0.2)
    try:
        reg.launch(f'{PY} -c "input()"', session_id="short", timeout=5)
        time.sleep(0.4)
        with pytest.raises(SessionNotFoundError):
            reg.get("short")
    finally:
        reg.close_all()


def test_close_reaps_process():
    reg = SessionRegistry(max_sessions=2, ttl_s=0)
    s = reg.launch(f'{PY} -c "input()"', session_id="x", timeout=5)
    pid = s.process.pid
    reg.close("x")
    import os

    time.sleep(0.2)
    with pytest.raises(OSError):
        os.kill(pid, 0)  # process must be gone
