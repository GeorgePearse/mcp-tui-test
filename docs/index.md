# MCP TUI Test

**Like Playwright, but for Terminal User Interfaces**

An MCP (Model Context Protocol) server that enables AI assistants to test Terminal User Interface (TUI) applications. This server provides tools to launch, interact with, and verify TUI applications programmatically.

**[View on GitHub](https://github.com/GeorgePearse/mcp-tui-test)** | **[See Examples](examples.md)**

## Features

- **Dual Testing Modes**: Choose between stream mode (for CLI tools) or buffer mode (for full TUIs with position awareness)
- **Launch TUI Applications**: Start any terminal-based application with configurable dimensions
- **Send Keyboard Input**: Simulate user typing, special keys, and control combinations
- **Capture Screen Output**: Read and analyze the current terminal display
- **Position-Based Testing**: Verify text at specific screen coordinates (buffer mode)
- **Cursor Tracking**: Monitor cursor position in real-time (buffer mode)
- **Wait for Text**: Asynchronously wait for specific content to appear
- **Assertions**: Verify that expected content is present in the output
- **Session Management**: Run multiple TUI applications simultaneously

## Testing Modes

### Stream Mode (Default)
- **Best for**: CLI tools, command-line applications, simple interactive programs
- **Uses**: pexpect for stream-based testing
- **Features**: Text matching, pattern waiting, output capture
- **Example use cases**: git, npm, grep, interactive shell scripts

### Buffer Mode
- **Best for**: Full TUI applications, ncurses apps, dialog boxes, menus
- **Uses**: pexpect + pyte for screen buffer emulation
- **Features**: All stream features PLUS position-based assertions, cursor tracking, region extraction
- **Example use cases**: htop, vim, dialog, interactive menus

**When to use which mode:**
- Use **stream mode** for applications that output text sequentially
- Use **buffer mode** for applications that draw complex UIs with cursor movement

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install the package:

```bash
pip install -e .
```

## Usage

### Running the MCP Server

```bash
python server.py
```

Or if installed as a package:

```bash
mcp-tui-test
```

### Configure in Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tui-test": {
      "command": "python",
      "args": ["/path/to/mcp-tui-test/server.py"]
    }
  }
}
```

Or if installed as a package:

```json
{
  "mcpServers": {
    "tui-test": {
      "command": "mcp-tui-test"
    }
  }
}
```

## Available Tools

### `launch_tui`
Launch a TUI application for testing.

**Parameters:**
- `command` (required): The command to launch the TUI application
- `session_id` (optional): Unique identifier for this session (default: "default")
- `timeout` (optional): Command timeout in seconds (default: 30)
- `dimensions` (optional): Terminal dimensions as WIDTHxHEIGHT (default: "80x24")
- `mode` (optional): Testing mode - "stream" or "buffer" (default: "stream")

**Examples:**
```python
# Stream mode for CLI tools
launch_tui(command="python example_tui_app.py", session_id="test1")

# Buffer mode for full TUI applications
launch_tui(command="htop", session_id="test2", mode="buffer", dimensions="120x40")
```

### `send_keys`
Send keyboard input to a TUI application.

**Parameters:**
- `keys` (required): Keys to send. Use `\n` for Enter, `\t` for Tab, `\x1b` for Escape
- `session_id` (optional): Session identifier (default: "default")
- `delay` (optional): Delay in seconds after sending keys (default: 0.1)

**Example:**
```python
send_keys(keys="1\n", session_id="test1")
```

### `send_ctrl`
Send a Ctrl+Key combination to the TUI application.

**Parameters:**
- `key` (required): The key to combine with Ctrl (e.g., 'c', 'd', 'z')
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```python
send_ctrl(key="c", session_id="test1")
```

### `capture_screen`
Capture the current screen output of a TUI application.

**Parameters:**
- `session_id` (optional): Session identifier (default: "default")
- `include_ansi` (optional): Whether to include ANSI escape codes in stream mode (default: False)
- `use_buffer` (optional): Force buffer/stream mode. Auto-detects if None (default: None)

**Examples:**
```python
# Auto-detect mode based on session
capture_screen(session_id="test1")

# Force buffer mode capture
capture_screen(session_id="test1", use_buffer=True)
```

### `expect_text`
Wait for specific text to appear in the TUI output.

**Parameters:**
- `pattern` (required): Text or regex pattern to wait for
- `session_id` (optional): Session identifier (default: "default")
- `timeout` (optional): Maximum time to wait in seconds (default: 10)

**Example:**
```python
expect_text(pattern="Welcome", session_id="test1", timeout=5)
```

### `assert_contains`
Assert that the current screen contains specific text.

**Parameters:**
- `text` (required): Text to search for in the current screen
- `session_id` (optional): Session identifier (default: "default")
- `use_buffer` (optional): Check buffer/stream mode. Auto-detects if None (default: None)

**Example:**
```python
assert_contains(text="Counter value: 1", session_id="test1")
```

### `assert_at_position` (Buffer Mode Only)
Assert that specific text appears at a screen position.

**Parameters:**
- `text` (required): Text to verify at the position
- `row` (required): Row number (0-indexed)
- `col` (required): Column number (0-indexed)
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```python
# Verify "Error" appears at row 5, column 10
assert_at_position(text="Error", row=5, col=10, session_id="test1")
```

### `get_cursor_position` (Buffer Mode Only)
Get the current cursor position.

**Parameters:**
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```python
get_cursor_position(session_id="test1")
# Returns: "Cursor position (session: test1): row 10, column 25"
```

### `get_screen_region` (Buffer Mode Only)
Extract a rectangular region of the screen.

**Parameters:**
- `row_start` (required): Starting row (0-indexed, inclusive)
- `row_end` (required): Ending row (0-indexed, exclusive)
- `col_start` (optional): Starting column (0-indexed, inclusive, default: 0)
- `col_end` (optional): Ending column (0-indexed, exclusive, default: end of line)
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```python
# Extract rows 5-10, full width
get_screen_region(row_start=5, row_end=10, session_id="test1")

# Extract rows 5-10, columns 20-60
get_screen_region(row_start=5, row_end=10, col_start=20, col_end=60, session_id="test1")
```

### `get_line` (Buffer Mode Only)
Get a specific line from the screen buffer.

**Parameters:**
- `row` (required): Row number (0-indexed)
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```python
get_line(row=3, session_id="test1")
# Returns: "Line 3 (session: test1): [line content]"
```

### `close_session`
Close a TUI testing session.

**Parameters:**
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```python
close_session(session_id="test1")
```

### `list_sessions`
List all active TUI testing sessions.

**Example:**
```python
list_sessions()
```

## Example Test Scenario

Here's how you might use this MCP to test a TUI application:

1. **Launch the application**:
   ```python
   launch_tui(command="python example_tui_app.py")
   ```

2. **Wait for it to load**:
   ```python
   expect_text(pattern="Welcome to the Example TUI Application")
   ```

3. **Interact with it**:
   ```python
   send_keys(keys="1\n")
   ```

4. **Verify output**:
   ```python
   assert_contains(text="Hello, TUI Tester!")
   ```

5. **Clean up**:
   ```python
   close_session()
   ```

## Testing the Example App

This repository includes an example TUI application (`example_tui_app.py`) that you can use to test the MCP server.

Run it directly:
```bash
python example_tui_app.py
```

Or test it through the MCP:
```python
launch_tui(command="python example_tui_app.py")
send_keys(keys="1\n")
capture_screen()
```

## Use Cases

- **Automated Testing**: Verify TUI applications behave correctly
- **Integration Testing**: Test command-line tools and interactive CLIs
- **Documentation**: Generate screenshots and examples from TUI apps
- **Debugging**: Inspect the state of TUI applications during development
- **CI/CD**: Add TUI testing to your continuous integration pipeline

## Technical Details

This MCP server uses:
- **FastMCP**: For the MCP server implementation
- **pexpect**: For spawning and controlling terminal applications
- **pyte**: For terminal emulation and screen buffer management (buffer mode)
- **ScreenSession wrapper**: Combines pexpect and pyte for hybrid testing

### Architecture
- **Stream Mode**: pexpect directly captures output stream
- **Buffer Mode**: pexpect output → pyte terminal emulator → screen buffer
- **Auto-detection**: Tools automatically use appropriate mode based on session

## Limitations

- Currently designed for Unix-like systems (Linux, macOS)
- Windows support may require modifications (consider using `winpty` or similar)
- Mouse support in TUIs is not currently available
- Buffer mode requires slightly more memory for screen emulation
- Position-based assertions only work in buffer mode

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details

## Related Projects

- [Playwright](https://playwright.dev/) - Browser automation (inspiration for this project)
- [pexpect](https://pexpect.readthedocs.io/) - Python module for spawning child applications
- [pyte](https://pyte.readthedocs.io/) - Python terminal emulator
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol specification

## Author

Created for testing TUI applications with AI assistance.
