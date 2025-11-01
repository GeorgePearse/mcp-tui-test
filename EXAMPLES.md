# TUI Testing Examples

This document provides practical examples of using the MCP TUI Test server.

## Example 1: Basic Menu Navigation

Testing the included example TUI application:

```
# Launch the application
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

## Example 2: Testing Multiple Sessions

Running multiple TUI apps simultaneously:

```
# Launch first app
launch_tui(command="python example_tui_app.py", session_id="app1")

# Launch second app
launch_tui(command="python example_tui_app.py", session_id="app2")

# List active sessions
list_sessions()

# Interact with first app
send_keys(keys="1\n", session_id="app1")
assert_contains(text="Hello", session_id="app1")

# Interact with second app
send_keys(keys="2\n", session_id="app2")
assert_contains(text="Info", session_id="app2")

# Close both sessions
close_session(session_id="app1")
close_session(session_id="app2")
```

## Example 3: Testing a CLI Tool

Testing `htop` or similar TUI applications:

```
# Launch htop
launch_tui(command="htop", dimensions="120x40")

# Wait for it to render
expect_text(pattern="CPU", timeout=5)

# Send 'q' to quit
send_keys(keys="q")

# Close session
close_session()
```

## Example 4: Using Control Keys

Testing applications that use Ctrl combinations:

```
# Launch a text editor like nano
launch_tui(command="nano test.txt")

# Type some text
send_keys(keys="Hello, World!")

# Save with Ctrl+O
send_ctrl(key="o")

# Confirm filename
send_keys(keys="\n")

# Exit with Ctrl+X
send_ctrl(key="x")

close_session()
```

## Example 5: Testing with Custom Dimensions

For TUIs that adapt to screen size:

```
# Test with small terminal
launch_tui(
    command="python example_tui_app.py",
    session_id="small",
    dimensions="40x10"
)

# Test with large terminal
launch_tui(
    command="python example_tui_app.py",
    session_id="large",
    dimensions="200x60"
)

# Capture and compare outputs
capture_screen(session_id="small")
capture_screen(session_id="large")

close_session(session_id="small")
close_session(session_id="large")
```

## Example 6: Debugging with Screen Capture

Debugging a failing test:

```
launch_tui(command="python my_app.py")

# Try an operation
send_keys(keys="some_command\n")

# Capture the current state for debugging
capture_screen(include_ansi=True)

# Try to find expected text
result = expect_text(pattern="Success", timeout=5)

# If it fails, capture again to see what happened
capture_screen()

close_session()
```

## Example 7: Testing Error Handling

Verify your TUI handles errors gracefully:

```
launch_tui(command="python example_tui_app.py")

# Send invalid input
send_keys(keys="invalid\n")

# Verify error message appears
assert_contains(text="Unknown option")

# Verify app is still responsive
send_keys(keys="1\n")
assert_contains(text="Hello")

close_session()
```

## Example 8: Testing Special Keys

Using escape sequences for special keys:

```
launch_tui(command="python my_menu_app.py")

# Tab key
send_keys(keys="\t")

# Escape key
send_keys(keys="\x1b")

# Enter key
send_keys(keys="\n")

# Arrow keys (if supported by pexpect)
send_keys(keys="\x1b[A")  # Up arrow
send_keys(keys="\x1b[B")  # Down arrow
send_keys(keys="\x1b[C")  # Right arrow
send_keys(keys="\x1b[D")  # Left arrow

close_session()
```

## Tips for Effective TUI Testing

1. **Add delays**: Some TUI apps need time to render. Use the `delay` parameter in `send_keys()`.

2. **Use expect_text for async operations**: When waiting for slow operations, use `expect_text()` instead of `capture_screen()`.

3. **Strip ANSI codes**: By default, `capture_screen()` removes ANSI escape codes for easier text matching.

4. **Test with different terminal sizes**: TUI apps often behave differently on various screen sizes.

5. **Use session IDs**: When testing multiple scenarios, use descriptive session IDs for clarity.

6. **Capture on failure**: Always capture the screen state when an assertion fails for debugging.

7. **Clean up sessions**: Always close sessions when done to free resources.

## Common Patterns

### Wait and Verify Pattern
```
launch_tui(command="my_app")
expect_text(pattern="Ready")
send_keys(keys="command\n")
assert_contains(text="Expected result")
close_session()
```

### Retry Pattern
```
launch_tui(command="my_app")

for attempt in range(3):
    send_keys(keys="retry_command\n")
    result = expect_text(pattern="Success", timeout=2)
    if "Found" in result:
        break

close_session()
```

### State Inspection Pattern
```
launch_tui(command="my_app")
send_keys(keys="some_action\n")
state = capture_screen()
# Analyze the state and decide next action based on content
close_session()
```
