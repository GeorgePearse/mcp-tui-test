#!/usr/bin/env python3
"""
MCP Server for TUI Testing
Like Playwright, but for Terminal User Interfaces
"""

import asyncio
import pexpect
import base64
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("tui-test")

# Store active TUI sessions
sessions: Dict[str, pexpect.spawn] = {}


@mcp.tool()
def launch_tui(
    command: str,
    session_id: str = "default",
    timeout: int = 30,
    dimensions: Optional[str] = "80x24"
) -> str:
    """
    Launch a TUI application for testing.

    Args:
        command: The command to launch the TUI application
        session_id: Unique identifier for this session (default: "default")
        timeout: Command timeout in seconds (default: 30)
        dimensions: Terminal dimensions as WIDTHxHEIGHT (default: "80x24")

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

        # Launch the TUI application
        session = pexpect.spawn(
            command,
            timeout=timeout,
            dimensions=(height, width),
            encoding='utf-8'
        )

        sessions[session_id] = session

        # Give it a moment to initialize
        asyncio.sleep(0.5)

        return f"✓ Launched TUI application (session: {session_id})\nCommand: {command}\nDimensions: {width}x{height}"

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

        # Send the keys
        session.send(keys)

        # Wait for the application to process
        import time
        time.sleep(delay)

        return f"✓ Sent keys to session {session_id}"

    except Exception as e:
        return f"✗ Failed to send keys: {str(e)}"


@mcp.tool()
def capture_screen(
    session_id: str = "default",
    include_ansi: bool = False
) -> str:
    """
    Capture the current screen output of a TUI application.

    Args:
        session_id: Session identifier (default: "default")
        include_ansi: Whether to include ANSI escape codes (default: False)

    Returns:
        Current screen content
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]

        # Get the current screen content
        output = session.before if session.before else ""

        if not include_ansi:
            # Strip ANSI escape codes
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output)

        return f"Screen output (session: {session_id}):\n{'='*60}\n{output}\n{'='*60}"

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
        session.timeout = timeout

        # Wait for the pattern
        index = session.expect([pattern, pexpect.TIMEOUT, pexpect.EOF])

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
    session_id: str = "default"
) -> str:
    """
    Assert that the current screen contains specific text.

    Args:
        text: Text to search for in the current screen
        session_id: Session identifier (default: "default")

    Returns:
        Success or failure message
    """
    try:
        if session_id not in sessions:
            return f"✗ No active session found: {session_id}"

        session = sessions[session_id]
        output = session.before if session.before else ""

        if text in output:
            return f"✓ Assertion passed: Found '{text}' in output"
        else:
            return f"✗ Assertion failed: '{text}' not found in output"

    except Exception as e:
        return f"✗ Failed to assert: {str(e)}"


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
        List of active session IDs
    """
    if not sessions:
        return "No active sessions"

    session_list = "\n".join([f"- {sid}" for sid in sessions.keys()])
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

        import time
        time.sleep(0.1)

        return f"✓ Sent Ctrl+{key.upper()} to session {session_id}"

    except Exception as e:
        return f"✗ Failed to send Ctrl+{key}: {str(e)}"


if __name__ == "__main__":
    mcp.run()
