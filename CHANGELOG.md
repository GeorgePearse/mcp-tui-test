# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`wait_for_text()`**: Wait for text on the *current* screen buffer (buffer
  mode), polling the live grid. Complements `expect_text()`, which matches the
  output stream including text that has scrolled off.

### Fixed
- **Buffer desync on animated TUIs**: `_update_buffer()` now drains all pending
  output instead of a single 8192-byte read, so the screen buffer renders the
  latest complete frame instead of stale/partial fragments.
- **Event-loop lag**: `launch_tui()`, `send_keys()`, and `send_ctrl()` are now
  async and use `asyncio.sleep()`, so waits no longer block the FastMCP event
  loop and stall the transport.
- **`expect_text()` timeout leak**: it no longer permanently overwrites the
  session process timeout, and runs the blocking wait off the event loop.

## [0.2.0] - 2025-01-11

### Added
- **Dual Testing Modes**: Stream mode (pexpect) and Buffer mode (pexpect + pyte)
- **ScreenSession wrapper class**: Combines pexpect and pyte for hybrid testing
- **Buffer mode tools**:
  - `assert_at_position()`: Assert text appears at specific screen coordinates
  - `get_cursor_position()`: Track cursor position in real-time
  - `get_screen_region()`: Extract rectangular regions of the screen
  - `get_line()`: Get specific lines from the screen buffer
- **Enhanced existing tools**:
  - `launch_tui()`: Added `mode` parameter to choose stream or buffer mode
  - `capture_screen()`: Added `use_buffer` parameter for mode override
  - `assert_contains()`: Added `use_buffer` parameter for mode override
  - `list_sessions()`: Now shows mode for each session

### Changed
- **pyte dependency**: Added pyte>=0.8.0 for screen buffer emulation
- **Performance**: ANSI escape regex compiled once for better performance
- **Session management**: Sessions now store ScreenSession objects instead of raw pexpect.spawn
- **Documentation**: Comprehensive updates to README.md and EXAMPLES.md
  - Added "Testing Modes" section explaining when to use each mode
  - Documented all new buffer-mode tools
  - Added 12+ new examples covering both modes
  - Updated technical details section

### Improved
- **Screen buffer awareness**: Buffer mode provides accurate screen state representation
- **Position-based testing**: Can now verify text at specific row/column coordinates
- **Cursor tracking**: Monitor cursor movement in TUI applications
- **Region extraction**: Extract and compare specific screen regions
- **Better TUI support**: Full support for ncurses-based applications

## [0.1.0] - 2025-01-11

### Added
- Initial release of MCP TUI Test server
- **Core functionality**:
  - `launch_tui()`: Launch TUI applications for testing
  - `send_keys()`: Send keyboard input
  - `send_ctrl()`: Send Ctrl+Key combinations
  - `capture_screen()`: Capture screen output
  - `expect_text()`: Wait for specific text to appear
  - `assert_contains()`: Assert text is present
  - `close_session()`: Close testing sessions
  - `list_sessions()`: List active sessions
- **Session management**: Support for multiple concurrent TUI sessions
- **Example application**: Simple interactive TUI app for testing
- **Documentation**: README.md and EXAMPLES.md with usage examples
- **FastMCP integration**: Built on FastMCP framework
- **pexpect integration**: Terminal process control and I/O

### Technical
- Python 3.10+ support
- FastMCP server implementation
- pexpect for process spawning and control
- Basic ANSI escape code stripping
