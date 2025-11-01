# MCP TUI Test

**Like Playwright, but for Terminal User Interfaces**

An MCP (Model Context Protocol) server that enables AI assistants to test Terminal User Interface (TUI) applications. This server provides tools to launch, interact with, and verify TUI applications programmatically.

## Features

- **Launch TUI Applications**: Start any terminal-based application with configurable dimensions
- **Send Keyboard Input**: Simulate user typing, special keys, and control combinations
- **Capture Screen Output**: Read and analyze the current terminal display
- **Wait for Text**: Asynchronously wait for specific content to appear
- **Assertions**: Verify that expected content is present in the output
- **Session Management**: Run multiple TUI applications simultaneously

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

**Example:**
```
launch_tui(command="python example_tui_app.py", session_id="test1", dimensions="100x30")
```

### `send_keys`
Send keyboard input to a TUI application.

**Parameters:**
- `keys` (required): Keys to send. Use `\n` for Enter, `\t` for Tab, `\x1b` for Escape
- `session_id` (optional): Session identifier (default: "default")
- `delay` (optional): Delay in seconds after sending keys (default: 0.1)

**Example:**
```
send_keys(keys="1\n", session_id="test1")
```

### `send_ctrl`
Send a Ctrl+Key combination to the TUI application.

**Parameters:**
- `key` (required): The key to combine with Ctrl (e.g., 'c', 'd', 'z')
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```
send_ctrl(key="c", session_id="test1")
```

### `capture_screen`
Capture the current screen output of a TUI application.

**Parameters:**
- `session_id` (optional): Session identifier (default: "default")
- `include_ansi` (optional): Whether to include ANSI escape codes (default: False)

**Example:**
```
capture_screen(session_id="test1")
```

### `expect_text`
Wait for specific text to appear in the TUI output.

**Parameters:**
- `pattern` (required): Text or regex pattern to wait for
- `session_id` (optional): Session identifier (default: "default")
- `timeout` (optional): Maximum time to wait in seconds (default: 10)

**Example:**
```
expect_text(pattern="Welcome", session_id="test1", timeout=5)
```

### `assert_contains`
Assert that the current screen contains specific text.

**Parameters:**
- `text` (required): Text to search for in the current screen
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```
assert_contains(text="Counter value: 1", session_id="test1")
```

### `close_session`
Close a TUI testing session.

**Parameters:**
- `session_id` (optional): Session identifier (default: "default")

**Example:**
```
close_session(session_id="test1")
```

### `list_sessions`
List all active TUI testing sessions.

**Example:**
```
list_sessions()
```

## Example Test Scenario

Here's how you might use this MCP to test a TUI application:

1. **Launch the application**:
   ```
   launch_tui(command="python example_tui_app.py")
   ```

2. **Wait for it to load**:
   ```
   expect_text(pattern="Welcome to the Example TUI Application")
   ```

3. **Interact with it**:
   ```
   send_keys(keys="1\n")
   ```

4. **Verify output**:
   ```
   assert_contains(text="Hello, TUI Tester!")
   ```

5. **Clean up**:
   ```
   close_session()
   ```

## Testing the Example App

This repository includes an example TUI application (`example_tui_app.py`) that you can use to test the MCP server.

Run it directly:
```bash
python example_tui_app.py
```

Or test it through the MCP:
```
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
- **Python asyncio**: For handling concurrent sessions

## Limitations

- Currently designed for Unix-like systems (Linux, macOS)
- Windows support may require modifications (consider using `winpty` or similar)
- Complex TUI frameworks (like `ncurses` with mouse support) may have limited testability
- ANSI escape sequences are stripped by default for easier text matching

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details

## Related Projects

- [Playwright](https://playwright.dev/) - Browser automation (inspiration for this project)
- [pexpect](https://pexpect.readthedocs.io/) - Python module for spawning child applications
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol specification

## Author

Created for testing TUI applications with AI assistance.
