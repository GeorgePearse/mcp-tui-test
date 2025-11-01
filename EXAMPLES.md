# TUI Testing Examples

This document provides practical examples of using the MCP TUI Test server in both stream and buffer modes.

## Stream Mode Examples

Stream mode is ideal for CLI tools and applications that output text sequentially.

### Example 1: Basic CLI Testing (Stream Mode)

Testing the included example TUI application:

```python
# Launch in stream mode (default)
launch_tui(command="python example_tui_app.py")

# Wait for the welcome message
expect_text(pattern="Welcome to the Example TUI Application")

# Select option 1 (Say Hello)
send_keys(keys="1\n")

# Verify the greeting appears
assert_contains(text="Hello, TUI Tester!")

# Select option 3 (Counter)
send_keys(keys="3\n")

# Verify counter incremented
assert_contains(text="Counter value: 1")

# Quit the application
send_keys(keys="q\n")

# Close the session
close_session()
```

### Example 2: Testing Git Commands (Stream Mode)

```python
# Launch git in stream mode
launch_tui(command="git status", session_id="git_test")

# Wait for output
expect_text(pattern="On branch", session_id="git_test", timeout=5)

# Capture the output
capture_screen(session_id="git_test")

# Close session
close_session(session_id="git_test")
```

### Example 3: Interactive Shell Script (Stream Mode)

```python
# Launch an interactive script
launch_tui(command="./interactive_setup.sh", session_id="setup")

# Answer prompts
send_keys(keys="yes\n", session_id="setup")
expect_text(pattern="Enter your name:", session_id="setup")

send_keys(keys="Alice\n", session_id="setup")
expect_text(pattern="Enter your email:", session_id="setup")

send_keys(keys="alice@example.com\n", session_id="setup")

# Verify completion
assert_contains(text="Setup complete", session_id="setup")

close_session(session_id="setup")
```

## Buffer Mode Examples

Buffer mode is ideal for full TUI applications with cursor positioning and screen layouts.

### Example 4: Testing TUI Menus (Buffer Mode)

```python
# Launch in buffer mode for position-aware testing
launch_tui(command="python menu_app.py", mode="buffer", session_id="menu")

# Wait for menu to render
expect_text(pattern="Main Menu", session_id="menu")

# Verify title is at the top
assert_at_position(text="Main Menu", row=0, col=0, session_id="menu")

# Navigate menu with arrow keys
send_keys(keys="\x1b[B", session_id="menu")  # Down arrow
send_keys(keys="\x1b[B", session_id="menu")  # Down arrow

# Check cursor moved
cursor_pos = get_cursor_position(session_id="menu")
# Should show cursor at row 2

# Select menu item
send_keys(keys="\n", session_id="menu")

close_session(session_id="menu")
```

### Example 5: Testing Dialog Boxes (Buffer Mode)

```python
# Launch dialog application in buffer mode
launch_tui(
    command='dialog --msgbox "Hello World" 10 30',
    mode="buffer",
    session_id="dialog",
    dimensions="80x24"
)

# Wait for dialog to appear
expect_text(pattern="Hello World", session_id="dialog")

# Verify message is centered (approximately row 5)
region = get_screen_region(row_start=3, row_end=7, session_id="dialog")
# Region should contain "Hello World"

# Press Enter to close
send_keys(keys="\n", session_id="dialog")

close_session(session_id="dialog")
```

### Example 6: Testing htop (Buffer Mode)

```python
# Launch htop in buffer mode
launch_tui(
    command="htop",
    mode="buffer",
    session_id="htop",
    dimensions="120x40"
)

# Wait for it to render
expect_text(pattern="CPU", session_id="htop", timeout=5)

# Verify CPU header is at top
assert_at_position(text="CPU", row=0, col=0, session_id="htop")

# Get the header region
header = get_screen_region(row_start=0, row_end=5, session_id="htop")

# Should contain CPU, Mem, Swp

# Navigate with keys
send_keys(keys="t", session_id="htop")  # Toggle tree view
send_keys(keys="u", session_id="htop")  # Filter by user

# Quit htop
send_keys(keys="q", session_id="htop")

close_session(session_id="htop")
```

### Example 7: Position-Based Assertions (Buffer Mode)

```python
# Launch application with structured layout
launch_tui(
    command="python dashboard.py",
    mode="buffer",
    session_id="dash",
    dimensions="100x30"
)

# Wait for dashboard to load
expect_text(pattern="Dashboard", session_id="dash")

# Verify title at specific position
assert_at_position(text="Dashboard", row=0, col=35, session_id="dash")

# Check status indicator at bottom right
assert_at_position(text="Status: OK", row=29, col=80, session_id="dash")

# Extract sidebar (first 20 columns)
sidebar = get_screen_region(
    row_start=1,
    row_end=28,
    col_start=0,
    col_end=20,
    session_id="dash"
)

# Sidebar should contain menu items
assert "Menu" in sidebar
assert "Settings" in sidebar

# Get specific line
line_5 = get_line(row=5, session_id="dash")

close_session(session_id="dash")
```

### Example 8: Cursor Tracking (Buffer Mode)

```python
# Launch text editor
launch_tui(
    command="nano test.txt",
    mode="buffer",
    session_id="nano",
    dimensions="80x24"
)

# Wait for nano to start
expect_text(pattern="GNU nano", session_id="nano")

# Type some text
send_keys(keys="Hello, World!", session_id="nano")

# Check cursor position (should have moved)
pos = get_cursor_position(session_id="nano")
# Should show cursor moved to the right

# Move cursor with arrows
send_keys(keys="\x1b[D" * 6, session_id="nano")  # Left arrow 6 times

# Check cursor moved back
pos = get_cursor_position(session_id="nano")

# Exit without saving
send_ctrl(key="x", session_id="nano")
send_keys(keys="n\n", session_id="nano")

close_session(session_id="nano")
```

## Advanced Examples

### Example 9: Testing Multiple Sessions

Running multiple TUI apps simultaneously:

```python
# Launch first app in stream mode
launch_tui(command="python cli_tool.py", session_id="app1")

# Launch second app in buffer mode
launch_tui(
    command="htop",
    session_id="app2",
    mode="buffer",
    dimensions="120x40"
)

# List active sessions
list_sessions()
# Should show: app1 (stream), app2 (buffer)

# Interact with first app
send_keys(keys="status\n", session_id="app1")
assert_contains(text="Running", session_id="app1")

# Interact with second app
send_keys(keys="t", session_id="app2")
assert_at_position(text="CPU", row=0, col=0, session_id="app2")

# Close both sessions
close_session(session_id="app1")
close_session(session_id="app2")
```

### Example 10: Region Extraction for Comparison (Buffer Mode)

```python
# Launch application
launch_tui(
    command="python status_app.py",
    mode="buffer",
    session_id="status"
)

# Wait for initial render
expect_text(pattern="System Status", session_id="status")

# Capture initial state of status region
initial_status = get_screen_region(
    row_start=10,
    row_end=15,
    col_start=0,
    col_end=50,
    session_id="status"
)

# Trigger a change
send_keys(keys="r", session_id="status")  # Refresh

# Wait a moment
send_keys(keys="", session_id="status", delay=1.0)

# Capture updated state
updated_status = get_screen_region(
    row_start=10,
    row_end=15,
    col_start=0,
    col_end=50,
    session_id="status"
)

# Compare regions
if initial_status != updated_status:
    print("Status region changed as expected")

close_session(session_id="status")
```

### Example 11: Testing Progress Bars (Buffer Mode)

```python
# Launch app with progress bar
launch_tui(
    command="python download_simulator.py",
    mode="buffer",
    session_id="progress"
)

# Wait for progress bar to appear
expect_text(pattern="Downloading", session_id="progress")

# Check progress bar at specific line
progress_line = get_line(row=5, session_id="progress")

# Should contain progress indicator like [====    ] 50%
assert "[" in progress_line

# Wait for completion
expect_text(pattern="Complete", session_id="progress", timeout=30)

# Verify final progress
final_progress = get_line(row=5, session_id="progress")
assert "100%" in final_progress

close_session(session_id="progress")
```

### Example 12: Using Control Keys (Both Modes)

```python
# Stream mode example - canceling a process
launch_tui(command="python long_running_task.py", session_id="task")

# Let it run for a bit
send_keys(keys="", session_id="task", delay=2.0)

# Cancel with Ctrl+C
send_ctrl(key="c", session_id="task")

# Verify cancellation
assert_contains(text="Cancelled", session_id="task")

close_session(session_id="task")

# Buffer mode example - quitting htop
launch_tui(command="htop", mode="buffer", session_id="htop2")

expect_text(pattern="CPU", session_id="htop2")

# Quit with 'q' key
send_keys(keys="q", session_id="htop2")

close_session(session_id="htop2")
```

## Tips for Effective TUI Testing

### When to Use Stream vs Buffer Mode

**Use Stream Mode for:**
- Command-line tools (git, npm, curl)
- Simple interactive scripts
- Applications that primarily output text
- When you only need to check if text appears (not where)

**Use Buffer Mode for:**
- Full-screen TUI applications (htop, vim, nano)
- Applications with menus and dialogs
- When you need to verify layout and positioning
- When you need cursor position tracking
- Applications that use ncurses or similar

### Best Practices

1. **Add appropriate delays**: Some TUI apps need time to render
   ```python
   send_keys(keys="command\n", delay=0.5)
   ```

2. **Use expect_text for async operations**: When waiting for slow operations
   ```python
   expect_text(pattern="Done", timeout=30)
   ```

3. **Capture screen on failure**: For debugging
   ```python
   try:
       assert_at_position(text="Expected", row=5, col=10)
   except:
       debug_output = capture_screen(use_buffer=True)
       print(debug_output)
   ```

4. **Test with appropriate terminal sizes**: Match your target environment
   ```python
   launch_tui(command="app", dimensions="132x43")  # Larger terminal
   ```

5. **Use sessions for isolation**: Each test can have its own session
   ```python
   launch_tui(command="test1", session_id="test1")
   launch_tui(command="test2", session_id="test2")
   ```

6. **Clean up sessions**: Always close when done
   ```python
   try:
       # ... test code ...
   finally:
       close_session(session_id="test")
   ```

## Common Patterns

### Wait and Verify Pattern
```python
launch_tui(command="app", mode="buffer")
expect_text(pattern="Ready")
send_keys(keys="action\n")
assert_at_position(text="Success", row=10, col=0)
close_session()
```

### Region Comparison Pattern
```python
launch_tui(command="app", mode="buffer")
before = get_screen_region(row_start=5, row_end=10)
send_keys(keys="update\n")
after = get_screen_region(row_start=5, row_end=10)
assert before != after
close_session()
```

### Multi-Step Workflow Pattern
```python
launch_tui(command="wizard", mode="buffer")

# Step 1
expect_text(pattern="Step 1")
send_keys(keys="value1\n")

# Step 2
expect_text(pattern="Step 2")
send_keys(keys="value2\n")

# Step 3
expect_text(pattern="Step 3")
send_keys(keys="value3\n")

# Verify completion
assert_contains(text="Complete")
close_session()
```
