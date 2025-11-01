#!/usr/bin/env python3
"""
MCP Server for TUI Testing
Like Playwright, but for Terminal User Interfaces

Supports two modes:
- stream: Traditional pexpect stream-based testing (good for CLIs)
- buffer: Screen buffer testing with pyte (good for full TUIs)
"""

import asyncio
import pexpect
import pyte
import re
import time
from typing import Optional, Dict, Any, Tuple
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("tui-test")

# Compile ANSI escape regex once for performance
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class ScreenSession:
    """
    Wrapper combining pexpect and pyte for hybrid stream/buffer testing.

    Attributes:
        process: pexpect.spawn instance
        screen: pyte.Screen instance (buffer mode)
        stream: pyte.Stream instance (buffer mode)
        mode: "stream" or "buffer"
        dimensions: (width, height) tuple
    """

    def __init__(self, command: str, timeout: int, dimensions: Tuple[int, int], mode: str = "stream"):
        self.mode = mode
        self.dimensions = dimensions
        width, height = dimensions

        # Launch process with pexpect
        self.process = pexpect.spawn(
            command,
            timeout=timeout,
            dimensions=(height, width),
            encoding='utf-8'
        )

        # Initialize pyte screen buffer if in buffer mode
        if mode == "buffer":
            self.screen = pyte.Screen(width, height)
            self.stream = pyte.Stream(self.screen)
            # Start background task to feed output to pyte
            self._update_buffer()

    def _update_buffer(self):
        """Update pyte screen buffer with latest process output."""
        if self.mode != "buffer":
            return

        try:
            # Read available output without blocking
            output = self.process.read_nonblocking(size=8192, timeout=0.1)
            if output:
                self.stream.feed(output)
        except pexpect.TIMEOUT:
            pass  # No new output, that's fine
        except pexpect.EOF:
            pass  # Process ended

    def send(self, keys: str):
        """Send keys to the process."""
        self.process.send(keys)
        time.sleep(0.1)
        if self.mode == "buffer":
            self._update_buffer()

    def get_stream_output(self, include_ansi: bool = False) -> str:
        """Get stream-based output (pexpect.before)."""
        output = self.process.before if self.process.before else ""
        if not include_ansi:
            output = ANSI_ESCAPE.sub('', output)
        return output

    def get_buffer_display(self) -> str:
        """Get screen buffer display (pyte)."""
        if self.mode != "buffer":
            return "Buffer mode not enabled for this session"

        self._update_buffer()
        return "\n".join(line.rstrip() for line in self.screen.display)

    def get_buffer_line(self, row: int) -> str:
        """Get a specific line from the screen buffer."""
        if self.mode != "buffer":
            return "Buffer mode not enabled for this session"

        self._update_buffer()
        if 0 <= row < self.screen.lines:
            return "".join(char.data for char in self.screen.buffer[row].values())
        return ""

    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position (row, col)."""
        if self.mode != "buffer":
            return (-1, -1)

        self._update_buffer()
        return (self.screen.cursor.y, self.screen.cursor.x)

    def get_char_at(self, row: int, col: int) -> str:
        """Get character at specific position."""
        if self.mode != "buffer":
            return ""

        self._update_buffer()
        if 0 <= row < self.screen.lines and 0 <= col < self.screen.columns:
            char = self.screen.buffer[row].get(col)
            return char.data if char else " "
        return ""

    def close(self):
        """Close the session."""
        self.process.close()


# Store active TUI sessions
sessions: Dict[str, ScreenSession] = {}


@mcp.tool()
def launch_tui(
    command: str,
    session_id: str = "default",
    timeout: int = 30,
    dimensions: Optional[str] = "80x24",
    mode: str = "stream"
) -> str:
    """
    Launch a TUI application for testing.

    Args:
        command: The command to launch the TUI application
        session_id: Unique identifier for this session (default: "default")
        timeout: Command timeout in seconds (default: 30)
        dimensions: Terminal dimensions as WIDTHxHEIGHT (default: "80x24")
        mode: Testing mode - "stream" for CLI tools, "buffer" for full TUIs (default: "stream")

    Returns:
        Status message with session ID
    """
    try:
        # Parse dimensions
        if dimensions:
            width, height = map(int, dimensions.split('x'))
        else:
            width, height = 80, 24

        # Close existing session if it exists
        if session_id in sessions:
            sessions[session_id].close()
            del sessions[session_id]

        # Launch the TUI application
        session = ScreenSession(
            command=command,
            timeout=timeout,
            dimensions=(width, height),
            mode=mode
        )

        sessions[session_id] = session

        # Give it a moment to initialize
        time.sleep(0.5)

        return f"✓ Launched TUI application (session: {session_id})\nCommand: {command}\nDimensions: {width}x{height}\nMode: {mode}"

    except Exception as e:
        return f"✗ Failed to launch TUI: {str(e)}"


@mcp.tool()
def send_keys(
    keys: str,
    session_id: str = "default",
    delay: float = 0.1
) -> str:
    """
    Send keyboard input to a TUI application.

    Args:
        keys: Keys to send. Special keys: \\n (Enter), \\t (Tab), \\x1b (Escape)
        session_id: Session identifier (default: "default")
        delay: Delay in seconds after sending keys (default: 0.1)

    Returns:
        Status message
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]
        session.send(keys)

        # Additional delay if requested
        if delay > 0.1:
            time.sleep(delay - 0.1)

        return f"✓ Sent keys to session {session_id}"

    except Exception as e:
        return f"✗ Failed to send keys: {str(e)}"


@mcp.tool()
def capture_screen(
    session_id: str = "default",
    include_ansi: bool = False,
    use_buffer: Optional[bool] = None
) -> str:
    """
    Capture the current screen output of a TUI application.

    Args:
        session_id: Session identifier (default: "default")
        include_ansi: Whether to include ANSI escape codes in stream mode (default: False)
        use_buffer: Force buffer mode if True, stream mode if False. Auto-detect if None (default: None)

    Returns:
        Current screen content
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        # Determine which mode to use
        if use_buffer is None:
            use_buffer = (session.mode == "buffer")

        if use_buffer and session.mode == "buffer":
            output = session.get_buffer_display()
            mode_label = "buffer"
        else:
            output = session.get_stream_output(include_ansi=include_ansi)
            mode_label = "stream"

        return f"Screen output (session: {session_id}, mode: {mode_label}):\n{'='*60}\n{output}\n{'='*60}"

    except Exception as e:
        return f"✗ Failed to capture screen: {str(e)}"


@mcp.tool()
def expect_text(
    pattern: str,
    session_id: str = "default",
    timeout: int = 10
) -> str:
    """
    Wait for specific text to appear in the TUI output.

    Args:
        pattern: Text or regex pattern to wait for
        session_id: Session identifier (default: "default")
        timeout: Maximum time to wait in seconds (default: 10)

    Returns:
        Status message indicating if text was found
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]
        session.process.timeout = timeout

        # Wait for the pattern
        index = session.process.expect([pattern, pexpect.TIMEOUT, pexpect.EOF])

        # Update buffer if in buffer mode
        if session.mode == "buffer":
            session._update_buffer()

        if index == 0:
            return f"✓ Found expected text: '{pattern}'"
        elif index == 1:
            return f"✗ Timeout waiting for: '{pattern}'"
        else:
            return f"✗ EOF reached before finding: '{pattern}'"

    except Exception as e:
        return f"✗ Failed to expect text: {str(e)}"


@mcp.tool()
def assert_contains(
    text: str,
    session_id: str = "default",
    use_buffer: Optional[bool] = None
) -> str:
    """
    Assert that the current screen contains specific text.

    Args:
        text: Text to search for in the current screen
        session_id: Session identifier (default: "default")
        use_buffer: Check buffer if True, stream if False. Auto-detect if None (default: None)

    Returns:
        Success or failure message
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        # Determine which mode to use
        if use_buffer is None:
            use_buffer = (session.mode == "buffer")

        if use_buffer and session.mode == "buffer":
            output = session.get_buffer_display()
        else:
            output = session.get_stream_output(include_ansi=False)

        if text in output:
            return f"✓ Assertion passed: Found '{text}' in output"
        else:
            return f"✗ Assertion failed: '{text}' not found in output"

    except Exception as e:
        return f"✗ Failed to assert: {str(e)}"


@mcp.tool()
def assert_at_position(
    text: str,
    row: int,
    col: int,
    session_id: str = "default"
) -> str:
    """
    Assert that specific text appears at a screen position (buffer mode only).

    Args:
        text: Text to verify at the position
        row: Row number (0-indexed)
        col: Column number (0-indexed)
        session_id: Session identifier (default: "default")

    Returns:
        Success or failure message
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        if session.mode != "buffer":
            return f"✗ Buffer mode required for position-based assertions. Session '{session_id}' is in stream mode."

        # Get text at position
        actual_text = ""
        for i, char in enumerate(text):
            actual_text += session.get_char_at(row, col + i)

        if actual_text.strip() == text.strip():
            return f"✓ Assertion passed: Found '{text}' at position ({row}, {col})"
        else:
            return f"✗ Assertion failed: Expected '{text}' at ({row}, {col}) but found '{actual_text.strip()}'"

    except Exception as e:
        return f"✗ Failed to assert at position: {str(e)}"


@mcp.tool()
def get_cursor_position(
    session_id: str = "default"
) -> str:
    """
    Get the current cursor position (buffer mode only).

    Args:
        session_id: Session identifier (default: "default")

    Returns:
        Cursor position as (row, col)
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        if session.mode != "buffer":
            return f"✗ Buffer mode required for cursor position. Session '{session_id}' is in stream mode."

        row, col = session.get_cursor_position()
        return f"Cursor position (session: {session_id}): row {row}, column {col}"

    except Exception as e:
        return f"✗ Failed to get cursor position: {str(e)}"


@mcp.tool()
def get_screen_region(
    row_start: int,
    row_end: int,
    col_start: int = 0,
    col_end: Optional[int] = None,
    session_id: str = "default"
) -> str:
    """
    Extract a rectangular region of the screen (buffer mode only).

    Args:
        row_start: Starting row (0-indexed, inclusive)
        row_end: Ending row (0-indexed, exclusive)
        col_start: Starting column (0-indexed, inclusive, default: 0)
        col_end: Ending column (0-indexed, exclusive, default: end of line)
        session_id: Session identifier (default: "default")

    Returns:
        Text content of the specified region
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        if session.mode != "buffer":
            return f"✗ Buffer mode required for region extraction. Session '{session_id}' is in stream mode."

        # Default col_end to screen width
        if col_end is None:
            col_end = session.dimensions[0]

        # Extract region
        region_lines = []
        for row in range(row_start, row_end):
            line = session.get_buffer_line(row)
            region_lines.append(line[col_start:col_end] if line else "")

        region_text = "\n".join(region_lines)

        return f"Screen region (session: {session_id}, rows {row_start}-{row_end-1}, cols {col_start}-{col_end-1}):\n{'='*60}\n{region_text}\n{'='*60}"

    except Exception as e:
        return f"✗ Failed to get screen region: {str(e)}"


@mcp.tool()
def get_line(
    row: int,
    session_id: str = "default"
) -> str:
    """
    Get a specific line from the screen buffer (buffer mode only).

    Args:
        row: Row number (0-indexed)
        session_id: Session identifier (default: "default")

    Returns:
        Text content of the specified line
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        if session.mode != "buffer":
            return f"✗ Buffer mode required for line extraction. Session '{session_id}' is in stream mode."

        line = session.get_buffer_line(row)
        return f"Line {row} (session: {session_id}): {line}"

    except Exception as e:
        return f"✗ Failed to get line: {str(e)}"


@mcp.tool()
def close_session(
    session_id: str = "default"
) -> str:
    """
    Close a TUI testing session.

    Args:
        session_id: Session identifier (default: "default")

    Returns:
        Status message
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]
        session.close()
        del sessions[session_id]

        return f"✓ Closed session: {session_id}"

    except Exception as e:
        return f"✗ Failed to close session: {str(e)}"


@mcp.tool()
def list_sessions() -> str:
    """
    List all active TUI testing sessions.

    Returns:
        List of active session IDs with their modes
    """
    if not sessions:
        return "No active sessions"

    session_list = "\n".join([f"- {sid} (mode: {session.mode})" for sid, session in sessions.items()])
    return f"Active sessions:\n{session_list}"


@mcp.tool()
def send_ctrl(
    key: str,
    session_id: str = "default"
) -> str:
    """
    Send a Ctrl+Key combination to the TUI application.

    Args:
        key: The key to combine with Ctrl (e.g., 'c', 'd', 'z')
        session_id: Session identifier (default: "default")

    Returns:
        Status message
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        # Convert key to control character
        ctrl_char = chr(ord(key.lower()) - ord('a') + 1)
        session.send(ctrl_char)

        return f"✓ Sent Ctrl+{key.upper()} to session {session_id}"

    except Exception as e:
        return f"✗ Failed to send Ctrl+{key}: {str(e)}"


if __name__ == "__main__":
    mcp.run()
