# Composing TUI tests in a coding harness

[Armin Ronacher's “What is Codemode” (2026-10-06)](https://lucumr.pocoo.org/2026/10/6/codemode/)
describes running orchestration code in the agent harness and calling tools from
that code. Applied to this project, it favors small TUI tools with predictable
structured results. The harness owns loops, branching, filtering, and orchestration;
this server owns the terminal processes and their screen state.

The existing tools already expose MCP `outputSchema` and `structuredContent`.
There is no need for an additional server-side JavaScript execution tool. A harness
can call these tools alongside its other tools without nesting one interpreter
inside another.

## Result contract

Use `result.structuredContent` for programmatic decisions. The serialized JSON text
in `content` is provided for compatibility. The
[MCP tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#structured-content)
defines this distinction.

Python and Go return the same set of fields for each tool on success and failure:

- `error` is a string when an operation fails and `null` otherwise.
- Assertion `found` and `screen_excerpt` are always present. `null` means no value;
  an empty string is an actual observation and must not be omitted.
- `list_sessions.sessions` is always an array, including when empty, and `reaped`
  is always an object mapping removed session IDs to reasons.
- `success: false` reports an operation failure. An assertion can return
  `success: true, passed: false`: the check ran, but the expectation did not hold.
- `expect_text.outcome` distinguishes `found`, `timeout`, `eof`, and `error`.

Also handle a rejected tool call or MCP `isError` response: argument validation
and transport failures can happen before a typed application result exists.

## A composed interaction

This example uses the article's JavaScript harness conventions (`tools` and `text`).
Tool prefixes depend on how your harness names the connection; discover its tools
and substitute the actual names. This code runs in that harness, not in Node.js
or in the TUI server.

```javascript
function checked(result) {
  if (result.isError) throw new Error(JSON.stringify(result.content));
  const data = result.structuredContent;
  if (!data || !data.success) {
    throw new Error(data?.error || data?.outcome || "Tool call failed");
  }
  return data;
}

// Choose a fresh ID: launching an existing ID replaces that session.
const session_id = "codemode-example-1";
checked(await tools.mcp__tui_test__launch_tui({
  command: "/bin/sh -c 'printf READY; read answer; printf DONE; read finish'",
  session_id,
  mode: "stream",
}));
try {
  checked(await tools.mcp__tui_test__expect_text({
    session_id, pattern: "READY", timeout: 5,
  }));
  checked(await tools.mcp__tui_test__send_keys({
    session_id, keys: "hello\n", raw: true,
  }));
  checked(await tools.mcp__tui_test__expect_text({
    session_id, pattern: "DONE", timeout: 5,
  }));
  const assertion = checked(await tools.mcp__tui_test__assert_contains({
    session_id, text: "DONE",
  }));
  // Return just the decision; keep full screens out of the model context unless needed.
  text({ passed: assertion.passed, excerpt: assertion.screen_excerpt });
} finally {
  const closed = await tools.mcp__tui_test__close_session({ session_id });
  if (closed.isError || !closed.structuredContent?.success) {
    text({ cleanupError: closed.structuredContent?.error || closed.content });
  }
}
```

## Ordering and execution boundaries

Await dependent operations on a session in order. Keyboard input, reads, waits,
and lifecycle operations all touch mutable state; concurrent calls on the same
session have no guaranteed ordering. Different session IDs can represent independent
workflows, but concurrency support and throughput differ between implementations.
The Python server's synchronous handlers can block other requests while waiting.
Do not rely on another parallel call to unblock a waiting `expect_text`.

Bound loops and timeouts, stay within the configured session cap (eight by default),
and close each session in `finally`. Reusing an ID is not an idempotent retry: a
launch replaces its process and repeated key presses repeat their effects. Session
IDs can be saved by a harness, but sessions are in memory, have a TTL, and do not
survive a server restart.

Commands execute on the MCP server's host, with that host's filesystem and
permissions. A sandbox around the harness's JavaScript does not sandbox the TUI
process. Text screen captures and `tui://{session_id}/screen` resources cross the
MCP boundary; local paths alone do not transfer files to a separate harness host.

## Contract verification

`tests/test_protocol.py` launches real servers over stdio, discovers the output
schemas, and validates structured results and compatibility text. CI runs the same
checks against both Python and the compiled Go binary. Locally:

```bash
uv venv && uv pip install -e ".[dev]"
(cd go && go build -o /tmp/mcp-tui-test ./cmd/mcp-tui-test)
MCP_TUI_TEST_BINARY=/tmp/mcp-tui-test uv run pytest tests/test_protocol.py -v
```
