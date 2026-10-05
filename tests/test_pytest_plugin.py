"""The pytest plugin, tested through its own fixture."""

import sys

import pytest

PY = sys.executable


def test_fixture_stream_roundtrip(tui):
    s = tui.launch(f'{PY} -c "print(\'PLUGIN OK\'); input()"', timeout=5)
    s.expect("PLUGIN OK", timeout=5)
    s.assert_contains("PLUGIN OK")
    s.send("bye\n")


def test_fixture_buffer_wait_until(tui):
    cmd = f"{PY} -c \"import sys; sys.stdout.write('\\x1b[2J\\x1b[2;3HHELLO'); sys.stdout.flush(); input()\""
    s = tui.launch(cmd, mode="buffer", dimensions=(40, 10), timeout=5)
    s.wait_until_contains("HELLO", timeout=5)
    s.assert_at("HELLO", 1, 2)


def test_fixture_assertion_failure_carries_screen(tui):
    s = tui.launch(f'{PY} -c "print(\'visible\'); input()"', timeout=5)
    s.expect("visible", timeout=5)
    with pytest.raises(AssertionError) as e:
        s.assert_contains("absent-text")
    assert "screen:" in str(e.value)
