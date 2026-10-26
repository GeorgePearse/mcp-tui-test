# TUI-testing landscape

Other tools that drive or snapshot terminal programs, what each one is built
on, and the ideas in each that are worth isolating. Repository facts (stars,
last push, language, dependencies) were read from the repositories themselves
on 2026-10-26. Where a line says *mcp-tui-test:* it describes what this project
does today; see the [synthesis](#synthesis) for the aggregate view.

## How mcp-tui-test fits

mcp-tui-test spawns the program under test in a real PTY (pexpect in Python,
`creack/pty` in Go) and optionally feeds its output through a VT emulator
(pyte in Python, `vt10x` in Go) to get a screen grid. It exposes that as MCP
tools with structured results, as a `tui://{session_id}/screen` resource, and
as a pytest fixture. It has text and regex waits, substring and position
assertions, region and line reads, cursor position, and session caps and
reaping. It has no idle or stable-screen wait, no style or colour reads, no
mouse or resize, no screenshots or recordings, no snapshot comparison, and no
scrollback.

## Tools

### microsoft/tui-test

[github.com/microsoft/tui-test](https://github.com/microsoft/tui-test)
(formerly `microsoft/shell-use`; the old URL redirects) · Rust · 295 stars ·
pushed 2026-10-23.

- **Approach**: real PTY on Windows, Linux and macOS, with a selectable
  emulator backend: Alacritty (default), Ghostty, Rio or xterm.js. One engine
  behind a CLI and in-process Rust, Python, JavaScript and Go libraries.
- **Assertions and snapshots**: Playwright-style text locators
  (`find`/`expect`/`click`/`highlight text`) with regex, whitespace, style
  (`--fg`, `--bold`, …), OSC 8 link and before/after-anchor filters; `expect
  snapshot NAME`; waits on idle, title, clipboard, bell, command, exit and
  shell readiness; `cells X Y W H` returns styled cells.
- **Capture**: SVG and PNG screenshots; APNG, GIF, MP4 and asciinema
  recordings; on-failure traces (`trace.md`, `trace.json`, `timeline.json`,
  `trace.html`).
- **Agent integration**: `agent-context` prints the command schema as JSON,
  `skill --add` installs an agent skill, `--json` everywhere, and a session
  daemon so each CLI call is one step.

Core ideas:

1. **Locators over the screen grid instead of byte-stream matching.** A locator
   is a query (text, regex, style, link, anchor) that resolves to cell spans
   and is retried until it passes. *mcp-tui-test:* has `assert_contains` and
   `assert_at_position`, but no query that returns match coordinates and no
   style or anchor filters.
2. **One engine, many front ends.** The CLI and four language bindings share
   one native core, so a test written for an agent and a test in a `cargo
   test` behave identically. *mcp-tui-test:* has the same shape in miniature
   (MCP server and pytest fixture share `core.py`), but Python and Go are
   separate implementations that share only the tool schema.
3. **Failure artefacts for agents first.** A failed assertion writes
   structured artefacts, and the docs tell agents to read `trace.md` and the
   JSON rather than the HTML. *mcp-tui-test:* attaches `screen_excerpt` to a
   failed assertion and nothing else.
4. **Swappable real emulators.** Backends are real terminal cores, so a test
   can be run against the emulator a user actually has. *mcp-tui-test:* one
   fixed emulator per language.

### antithesishq/bombadil

[github.com/antithesishq/bombadil](https://github.com/antithesishq/bombadil) ·
Rust · 1,564 stars · pushed 2026-10-23 ·
[manual](https://antithesishq.github.io/bombadil/).

- **Approach**: property-based testing of web and terminal UIs. Terminal mode
  runs the program on a real PTY (`portable-pty`) and parses its output with
  `libghostty-vt`. The loop is: extract state, check every property, pick the
  next action from the current state, perform it, wait for the next chunk of
  output or a timeout, repeat.
- **Assertions**: properties are TypeScript modules using temporal operators
  (`always`, `eventually`, `next`, `now`, `implies`) over a sequence of states.
  Terminal defaults include `exitSuccess` and `noReplacementChars`; the default
  action generator types Unicode input and escape sequences. `bombadil terminal
  shrink` reduces a violating trace to a shorter one (marked experimental).
- **Results**: Oskar Wickström's
  [2026-04-30 write-up](https://wickstrom.tech/2026-04-30-bombadil-terminal-experiment.html)
  reports a freeze in vitetris, two btop bugs (one already fixed in 1.4.6, one
  newly reported) and an rlwrap segfault from a few days of random input,
  scrolling and resizing at roughly 300 captured states per second.
- **Agent integration**: none; it is a CI and local tool with a GitHub Action.

Core ideas:

1. **Property-based exploration instead of scripted examples.** Random,
   state-aware action generation reaches sequences nobody scripted.
   *mcp-tui-test:* every action is chosen by the caller.
2. **Temporal properties over a state sequence.** Invariants are checked after
   every step, not at one chosen moment. *mcp-tui-test:* single-moment
   assertions only.
3. **Shrinking a violating trace.** A long random trace is reduced to a minimal
   reproduction. *mcp-tui-test:* no trace recording, so nothing to shrink.
4. **Default properties that need no spec.** "Exits zero" and "never prints a
   byte the terminal can't render" catch real bugs with zero configuration.
   *mcp-tui-test:* no built-in invariants.

### montanaflynn/headless-terminal (`ht`)

[github.com/montanaflynn/headless-terminal](https://github.com/montanaflynn/headless-terminal)
· Go · 121 stars · pushed 2026-08-31.

- **Approach**: a Unix-socket daemon owns one PTY per session and feeds output
  through `libghostty-vt` (statically linked via cgo); the `ht` CLI talks JSON
  lines to it. Vim-style key notation (`<CR>`, `<Esc>`, `<C-c>`).
- **Assertions and snapshots**: `ht view` in plain, ANSI, HTML, PNG or JSON;
  `ht wait` on text, cursor, idle, change or exit; asciicast recording via
  `ht record`; `ht watch` streams a session live to another pane.
- **Agent integration**: an Anthropic-format skill in
  `skills/headless-terminal/` that teaches the key notation and a
  "wait-strategy decision tree (the part agents get wrong)".

Core ideas:

1. **Send synchronisation as a first-class concept.** Default 20 ms keystroke
   pacing, plus `--wait-text`, `--wait-cursor`, `--wait-idle`, `--wait-change`
   and `--wait-exit` that compose with AND on the same `send`. *mcp-tui-test:*
   `send_keys` sleeps a fixed `delay` (default 0.1 s); waiting is a separate
   `expect_text` call and only on text.
2. **Daemon-owned sessions, thin CLI.** Sessions outlive any one command, so
   an agent issues one shell command per step. *mcp-tui-test:* equivalent via
   the MCP server process holding sessions.
3. **Shoulder-surfing.** `ht watch` lets a human see live what the agent is
   driving. *mcp-tui-test:* no live view.
4. **Skill as the integration surface.** Instead of an MCP server, a
   `SKILL.md` that teaches an agent when and how to call the CLI.
   *mcp-tui-test:* MCP tools only; no skill file.

### beorn/termless

[github.com/beorn/termless](https://github.com/beorn/termless) · TypeScript
(Bun and Node) · 36 stars · pushed 2026-10-24.

- **Approach**: a `TerminalBackend` interface with twelve implementations:
  xterm.js (default), Ghostty via WASM, Ghostty native, Alacritty, WezTerm,
  vt100 (TypeScript), vt100 (Rust), vt220, vterm.js, libvterm, Kitty and
  Peekaboo (drives a real macOS terminal through accessibility APIs). Tests can
  `feed()` bytes with no process, or `spawn()` a real PTY (Bun native, or
  `node-pty` on Node).
- **Assertions and snapshots**: region selectors (`screen`, `scrollback`,
  `buffer`, `viewport`, `row(n)`, `cell(r, c)`, `range`) and 21+ Vitest
  matchers for text, cell style, cursor, mode, title, scrollback and
  `toMatchTerminalSnapshot()`; `term.out` matches raw protocol bytes that
  render nothing (Kitty graphics, OSC 52). SVG and PNG screenshots;
  recordings in a `.tty`/`.ttyz` journal format with codecs to asciicast,
  `.tape` and ttyrec.
- **Agent integration**: `@termless/cli` ships `termless record`, `termless
  play` and an MCP server.

Core ideas:

1. **Multi-backend conformance.** The same test runs against every emulator,
   and a differential corpus mined from the emulators' own test suites grades
   backends against each other. *mcp-tui-test:* pyte and vt10x are
   implementation details, not selectable, and never compared.
2. **Three inlets, one path.** `feed()`, `spawn()` and a replayed recording all
   arrive at the backend as ordered byte writes, so an assertion written
   against a live process runs unchanged against a stored journal.
   *mcp-tui-test:* live PTY only.
3. **Region selectors separate "where" from "what".** `expect(term.row(0))`
   and `expect(term.cell(0, 8)).toHaveFg(…)` compose a location with a matcher.
   *mcp-tui-test:* `get_screen_region` and `get_line` return text; there is no
   cell-level style view.
4. **Raw-output assertions for invisible protocol.** Some behaviour changes no
   cell, so the byte stream stays inspectable next to the grid.
   *mcp-tui-test:* stream mode exposes the stream with ANSI optionally
   retained, but not alongside a grid in the same session.

### vyncint/termlens

[github.com/vyncint/termlens](https://github.com/vyncint/termlens) · Rust ·
27 stars · pushed 2026-10-23 · recommended in ratatui's
[snapshot-testing recipe](https://ratatui.rs/recipes/testing/snapshots/) as
the PTY layer to pair with `TestBackend`.

- **Approach**: real PTY, `vt100` crate behind an internal trait (with a
  second parser recovering blink, conceal and strikethrough, which `vt100`
  drops). A reader thread drains the PTY continuously and answers the queries a
  real terminal would answer (cursor position, DA, `DECRQM`, `XTGETTCAP`,
  background colour), so capability-probing apps do not hang. Every `Screen`
  is an immutable snapshot taken under one lock. Windows via ConPTY.
- **Assertions and snapshots**: `wait_until(pred)`, `wait_frame(pred)` for
  complete DEC 2026 synchronized frames, `snapshot_after(pred)`,
  `wait_stable`, `wait_idle`, `wait_exit`; `assert_screen_snapshot!` via
  insta; `mask_matching`, `mask_rect` and `mask_matches` blank volatile cells
  on the grid without shifting columns; `Screen::diff` reports cell-by-cell
  changes; `Screen::parse` reads a printed snapshot back in. Mode-aware
  input: mouse, paste and keys are encoded for the modes the app enabled.
  `graphics()` captures Kitty and sixel transmissions. A `termlens` CLI does
  `inspect`, `diff` and `render --svg`.
- **Agent integration**: none beyond the CLI and JSON output
  (`serde` feature).

Core ideas:

1. **Wait on a predicate over the screen, not on text.** Every wait takes a
   closure over the full `Screen` (cells, styles, cursor, modes, counters) and
   is deadline-bounded with the screen attached on timeout; there is no
   `sleep`. *mcp-tui-test:* `expect_text` waits on a regex over the stream;
   the pytest plugin's `wait_until_contains` polls the buffer text.
2. **Frame-complete snapshots.** `wait_frame` returns only complete DEC 2026
   frames, so a snapshot is never torn mid-repaint; `snapshot_after` waits for
   the predicate and then for stillness. *mcp-tui-test:* `capture_screen`
   reads whatever has arrived.
3. **Mask the grid, not the text.** Volatile content is replaced cell-for-cell
   so layout and styles still compare. *mcp-tui-test:* no snapshot
   comparison.
4. **Answer the terminal's questions.** Replying to capability probes is what
   lets real apps run under a fake terminal. *mcp-tui-test:* pexpect and pyte
   do not answer `CSI 6n` or DA requests; apps that wait for a reply stall
   until their own timeout.

### mwunsch/termscope

[github.com/mwunsch/termscope](https://github.com/mwunsch/termscope) · Zig ·
19 stars · pushed 2026-04-08.

- **Approach**: single static binary on `libghostty-vt`. `termscope snapshot
  -- cmd` for one-shot capture, `termscope exec` with `--wait-for-text`,
  `--type`, `--press`, `--wait-idle`, `--expect` for scripted runs, and
  `termscope session` as a JSON-lines request/response protocol over
  stdin/stdout. Emacs-style key notation (`C-c`, `M-x`, `RET`).
- **Assertions and snapshots**: `--expect TEXT` sets the exit code; output as
  numbered text ("optimized for LLMs"), style spans, JSON, HTML or SVG;
  `query` returns cursor, style, title and alt-screen state.
- **Agent integration**: `npx skills add mwunsch/termscope`.

Core ideas:

1. **JSON-lines session protocol on stdio.** A TUI driver that any harness can
   speak without an SDK or a daemon socket. *mcp-tui-test:* MCP over stdio
   plays the same role with a schema.
2. **Numbered-line text format for models.** Row numbers in the text output
   so an agent can refer to a line without counting. *mcp-tui-test:*
   `get_line(row)` exists but `capture_screen` returns unnumbered text.
3. **Exit-code assertions for CI.** `exec --expect` makes a one-liner a test.
   *mcp-tui-test:* assertion results are structured fields, not an exit code,
   because the caller is an MCP client.

### fcoury/termwright

[github.com/fcoury/termwright](https://github.com/fcoury/termwright) · Rust ·
23 stars · pushed 2026-02-10.

- **Approach**: `portable-pty` and the `vt100` crate, async (tokio). Library,
  CLI (`run`, `screenshot`, `run-steps` for YAML/JSON step files) and a
  `daemon` mode exposing a JSON-RPC Unix socket. Emulates replies to OSC
  10/11/12 colour queries and `CSI 6n` cursor-position requests.
- **Assertions and snapshots**: wait for text, regex, screen stability
  (`wait_for_idle`) or exit; screen as text or JSON with colours, cursor and
  cell attributes; PNG screenshots rendered with system fonts; box detection
  that finds UI boundaries from box-drawing characters.
- **Agent integration**: JSON screen output described as "for AI agents"; no
  MCP server or skill.

Core ideas:

1. **Box detection.** Deriving panel and dialog boundaries from box-drawing
   characters gives a semantic region without the app's cooperation.
   *mcp-tui-test:* regions are caller-specified coordinates.
2. **Declarative step files.** A YAML or JSON scenario replaces a program for
   simple E2E flows. *mcp-tui-test:* no scenario format; the harness scripts
   calls.
3. **Shell-scriptable daemon.** `socat` plus `jq` is enough to write tests.
   *mcp-tui-test:* needs an MCP client.

### charmbracelet/vhs

[github.com/charmbracelet/vhs](https://github.com/charmbracelet/vhs) · Go ·
21,201 stars · pushed 2026-10-01.

- **Approach**: a `.tape` DSL (`Type`, `Enter`, `Sleep`, `Wait /regex/`,
  `Set`, `Require`, `Hide`/`Show`, `Screenshot`, `Source`, `Env`) executed
  against `ttyd` serving xterm.js in a headless Chromium driven by `rod`;
  frames are assembled by `ffmpeg`. `vhs record` writes a tape from a live
  session.
- **Assertions and snapshots**: `Output golden.ascii` or `.txt` writes a text
  rendering for golden-file diffs in git; `Wait[+Screen][+Line] /regex/` is
  the only synchronisation primitive. GIF, MP4, WebM and PNG frame outputs.
- **Agent integration**: none built in. Agents use it to produce a GIF or
  `.ascii` they can read; testty compiles its scenarios to tapes for the same
  reason.

Core ideas:

1. **Tape DSL compiled to recordings.** One short script yields a
   reproducible demo and a golden text file. *mcp-tui-test:* no DSL and no
   recording.
2. **Golden text outputs from the same run as the video.** The `.ascii`
   render is the test; the GIF is the documentation. *mcp-tui-test:* no
   golden files.
3. **A real browser-hosted emulator.** Rendering through xterm.js in Chromium
   makes the picture match what a web-embedded terminal shows, at the cost of
   heavy dependencies. *mcp-tui-test:* lightweight emulator, no pixels.

### charmbracelet `x/exp/teatest`

[github.com/charmbracelet/x](https://github.com/charmbracelet/x) (package
`exp/teatest`, with a `v2` for Bubble Tea v2) · Go.

- **Approach**: in-process. `NewTestModel` runs a `tea.Model` with a fake
  terminal size; `Send(tea.Msg)` injects messages; `WaitFor(reader, cond)`
  polls the output reader; `FinalModel` and `FinalOutput` wait for the
  program to quit.
- **Assertions and snapshots**: `RequireEqualOutput` compares the final output
  bytes with a golden file in `testdata/`, updated with `-update`, diffed with
  the system `diff`.
- **Agent integration**: none.

Core ideas:

1. **Golden output of the final frame.** A single byte-exact file per test.
   *mcp-tui-test:* none.
2. **Inject messages, not keystrokes.** Tests speak the framework's own event
   type, skipping the terminal. *mcp-tui-test:* always keystrokes through a
   PTY, which is what you want when the app is a black box.

### ratatui `TestBackend` with insta

[ratatui.rs/recipes/testing/snapshots](https://ratatui.rs/recipes/testing/snapshots/)
· Rust.

- **Approach**: in-process. `Terminal::new(TestBackend::new(80, 20))`, draw
  the widget, `assert_snapshot!(terminal.backend())`. Snapshots are text,
  one row per line; colour is not included (ratatui issue #1402 is open for
  that). The recipe then points to termlens for the layers `TestBackend`
  cannot see: the event loop, raw mode, alternate screen, exit codes.
- **Agent integration**: none.

Core ideas:

1. **In-process buffer snapshots with a review workflow.** `cargo insta
   review` makes accepting intentional changes cheap. *mcp-tui-test:* none.
2. **Two layers, explicitly.** Widget tests in-process, a few flows through a
   PTY. *mcp-tui-test:* is the second layer only.

### Textual Pilot and pytest-textual-snapshot

[Textual testing guide](https://textual.textualize.io/guide/testing/) and
[github.com/Textualize/pytest-textual-snapshot](https://github.com/Textualize/pytest-textual-snapshot)
· Python · 52 stars · pushed 2025-04-26.

- **Approach**: in-process. `App.run_test()` runs the app headless and yields
  a `Pilot` with `press`, `click` (by CSS selector or offset, with modifiers
  and click counts), `hover` and `pause`; `size` is set on `run_test`.
- **Assertions and snapshots**: plain `assert` against widget state;
  `snap_compare(app, press=[…], run_before=…, terminal_size=…)` renders an
  SVG screenshot and compares it with the stored one; an HTML report shows
  the diff; `--snapshot-update` accepts changes.
- **Agent integration**: none.

Core ideas:

1. **Selector-addressed interaction.** `pilot.click("#number-5")` targets a
   widget, not a coordinate. Needs the framework's cooperation.
   *mcp-tui-test:* coordinates and text only.
2. **SVG screenshot as the snapshot artefact.** Diffable in a browser, styles
   included. *mcp-tui-test:* none.

### pexpect / expect, pyte, libvterm

[pexpect](https://pexpect.readthedocs.io/),
[expect](https://core.tcl-lang.org/expect/index), [pyte](https://pyte.readthedocs.io/),
[libvterm](https://www.leonerd.org.uk/code/libvterm/).

- **Approach**: pexpect and expect spawn a PTY and match the byte stream
  against patterns; pyte (Python) and libvterm (C, used by Neovim) are VT
  emulators that turn that stream into a grid. mcp-tui-test's Python
  implementation is pexpect plus pyte.
- **Assertions**: `expect(pattern)` with a timeout; pyte exposes
  `screen.display`, `screen.buffer[row][col]` with styles, and cursor;
  `HistoryScreen` adds scrollback.
- **Agent integration**: none.

Core ideas:

1. **Stream matching for sequential programs.** Cheap and exact when the
   program prints lines. *mcp-tui-test:* stream mode.
2. **Separate the PTY from the emulator.** Any stream can be fed to any
   emulator. *mcp-tui-test:* same split (`ScreenSession` owns both).

### testty

[docs.rs/testty](https://docs.rs/testty), source in
[github.com/agentty-xyz/agentty](https://github.com/agentty-xyz/agentty)
(`crates/testty`) · Rust. The `testty` crate exists on crates.io (0.18.1 as
of 2026-10-21); it is published from the agentty monorepo, and the latest
crate-level description there is agentty's rather than testty's.

- **Approach**: real PTY (`portable-pty`) with the `vt100` crate.
  `Scenario` builder (`wait_for_stable_frame`, `press_key`, `write_text`,
  `eventually`, `capture`) run against a `PtySessionBuilder`; a `testty run
  scenario.yaml` CLI for non-Rust projects. Answers DA1 so capability probes
  return immediately.
- **Assertions and snapshots**: `match_text_in_region`, recipes such as
  `expect_selected_tab` that read highlight styles; text or pixel baselines;
  "proof" reports as text, screenshot, GIF, HTML or JUnit XML. Feature GIFs
  are produced by compiling the same steps to a VHS `.tape`, hash-cached on
  the PTY frames and rendering settings so they re-record only when the UI
  changed.
- **Agent integration**: none specific.

Core ideas:

1. **Semantic recipes over styles.** "Selected tab" is defined by highlight
   attributes, not by text. *mcp-tui-test:* no style access.
2. **Compile scenarios to VHS tapes.** The test and the demo recording are the
   same steps. *mcp-tui-test:* none.
3. **Hash-cached recordings.** Re-render only when the frames changed.
   *mcp-tui-test:* none.

### hegner123/tui-test-ghost and mjpowersjr/vterm-mcp

[github.com/hegner123/tui-test-ghost](https://github.com/hegner123/tui-test-ghost)
· Zig · 2 stars · pushed 2026-05-16.
[github.com/mjpowersjr/vterm-mcp](https://github.com/mjpowersjr/vterm-mcp)
· Rust · 3 stars · pushed 2026-04-15.

Both exist. Both are MCP servers over a real PTY and `libghostty-vt`, so they
are the closest in shape to mcp-tui-test.

- **tui-test-ghost** tools: `tui_start`, `tui_send` (key tokens such as
  `down*3`, with `settle_ms`), `tui_screen`, `tui_cell` (char, bold, italic,
  underline, strikethrough, dim, fg, bg), `tui_wait` (text, `stable_ms`, or
  cursor position), `tui_resize`, `tui_snapshot` (`golden_path` compares or
  creates a baseline), `tui_stop`, `tui_record_start`/`stop` to a JSONL file,
  and `tui-test-ghost replay test.jsonl` that re-executes action tools and
  compares assertion tools' recorded results. Every tool accepts a `region`.
- **vterm-mcp** tools: `start_session`, `stop_session`, `list_sessions`,
  `get_screen` (text, cursor, optional per-cell styles), `send_keys` (named
  keys with `C-`, `M-`, `S-` prefixes), `wait_for_text` (substring or regex).

Core ideas:

1. **Record the MCP session, replay it as a test.** The agent's exploratory
   calls become a JSONL file; replay re-runs the actions and checks the
   recorded assertion results, turning an interactive session into a
   regression test. *mcp-tui-test:* no recording.
2. **Region parameter on every read.** Any tool can scope itself to a
   sub-rectangle, so screen text sent to the model stays small.
   *mcp-tui-test:* only `get_screen_region`.
3. **Golden snapshot as a tool.** `tui_snapshot` with a path compares or
   creates the baseline from inside the agent loop. *mcp-tui-test:* none.
4. **Settle time on send.** `settle_ms` and `stable_ms` wait for the screen
   to stop changing. *mcp-tui-test:* fixed `delay`.

### libghostty-vt and go-libghostty

[mitchellh.com/writing/libghostty-is-coming](https://mitchellh.com/writing/libghostty-is-coming)
(2025-09-22) and
[github.com/mitchellh/go-libghostty](https://github.com/mitchellh/go-libghostty)
· Go bindings · 155 stars · pushed 2026-10-21 (a mirror; source of truth is
on tangled.org).

libghostty-vt is "a zero-dependency library that provides an API for parsing
terminal sequences and maintaining terminal state", extracted from Ghostty.
It is the emulator under bombadil, `ht`, termscope, tui-test-ghost, vterm-mcp
and one of the backends of microsoft/tui-test and termless. go-libghostty is
a cgo binding that statically links it; its example feeds bytes to a
`Terminal` and formats the grid as plain text with a `Formatter`.

Mitchell Hashimoto did not build a TUI test framework. On 2026-04-30 he
[wrote](https://x.com/mitchellh/status/2049851176988914071):

> Libghostty can now be used to fuzz TUIs, thanks to @owickstrom +
> @AntithesisHQ. They already found bugs in multiple including btop. I always
> imagined libghostty would be useful for testing TUIs, super happy to see
> this is both practical and valuable.
>
> This is another example of where speed matters! "Why does Ghostty need to
> be so fast?" Well, if you're running hundreds or thousands of unit tests
> that each use a clean in-memory terminal, you want that to be fast. If
> you're fuzz testing and trying to push an unlimited amount of data through
> a terminal, you want that terminal to be fast.

Core ideas:

1. **A production emulator as a library.** The grid a test asserts on is the
   same code a real terminal renders, so emulator bugs are not the test's
   bugs. *mcp-tui-test:* pyte and vt10x are small independent emulators.
2. **Throughput as a testing feature.** Fast parsing is what makes thousands
   of in-memory terminals per test run and fuzzing at hundreds of states per
   second practical. *mcp-tui-test:* one session per PTY, speed not a goal.

## Synthesis

Idea by tool. A filled cell means the tool has the idea as a documented
feature. The last column is mcp-tui-test today.

| Idea | tui-test | bombadil | ht | termless | termlens | termscope | termwright | vhs | teatest | ratatui | Textual | testty | ghost / vterm-mcp | mcp-tui-test |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Real PTY | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | | ✓ | ✓ | ✓ |
| Production emulator (Ghostty, Alacritty, xterm.js, …) | ✓ | ✓ | ✓ | ✓ | | ✓ | | ✓ | | | | | ✓ | |
| Multi-backend conformance | ✓ | | | ✓ | | | | | | | | | | |
| Wait for idle / stable screen | ✓ | | ✓ | | ✓ | ✓ | ✓ | | | | | ✓ | ✓ | |
| Wait on predicate over full screen state | | ✓ | | | ✓ | | | | ✓ | | | ✓ | | |
| Frame-complete (DEC 2026) snapshots | | | | | ✓ | | | | | | | | | |
| Locators returning match coordinates | ✓ | | | | ✓ | ✓ | | | | | | | | |
| Cell styles and colours readable | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | | ✓ | ✓ | ✓ | |
| Region-scoped reads | ✓ | | | ✓ | ✓ | | | | | | | ✓ | ✓ | ✓ |
| Semantic regions (box detection, tab recipes) | | | | | | | ✓ | | | | ✓ | ✓ | | |
| Golden / snapshot comparison | ✓ | | | ✓ | ✓ | | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Grid masking of volatile cells | | | | | ✓ | | | | | | | | | |
| SVG / PNG screenshots | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | ✓ | ✓ | | |
| Recording (asciicast, GIF, tape) | ✓ | | ✓ | ✓ | | | | ✓ | | | | ✓ | | |
| Replay a recording through the same assertions | | | | ✓ | | | | | | | | | ✓ | |
| Tape / scenario DSL | | | | ✓ | | | ✓ | ✓ | | | | ✓ | | |
| Answers terminal capability queries | | | | | ✓ | | ✓ | | | | | ✓ | | |
| Mouse input | ✓ | | | ✓ | ✓ | | | | | | ✓ | | | |
| Resize / SIGWINCH | ✓ | ✓ | | ✓ | ✓ | ✓ | | | | | | | ✓ | |
| Scrollback | ✓ | ✓ | ✓ | ✓ | ✓ | | | | | | | | | |
| Property-based exploration with shrinking | | ✓ | | | | | | | | | | | | |
| Temporal properties over a trace | | ✓ | | | | | | | | | | | | |
| Structured (JSON) results | ✓ | | ✓ | | ✓ | ✓ | ✓ | | | | | | ✓ | ✓ |
| Failure artefacts beyond the message | ✓ | ✓ | | | ✓ | | | | | | ✓ | ✓ | | partial |
| MCP server | | | | ✓ | | | | | | | | | ✓ | ✓ |
| Agent skill file | ✓ | | ✓ | | | ✓ | | | | | | | | |
| Session daemon or server | ✓ | | ✓ | | | ✓ | ✓ | | | | | | ✓ | ✓ |
| Live human view of the session | ✓ | | ✓ | | | | | | | | | | | |
| In-process framework hooks | | | | | | | | | ✓ | ✓ | ✓ | | | |

"partial" for mcp-tui-test: failed assertions carry `screen_excerpt`; there
are no traces, screenshots or recordings.

## Ideas mcp-tui-test could adopt next

Ordered by payoff for an agent-driven TUI test server, highest first. This is
a list, not a plan; none of it is implemented.

1. **Wait for a stable screen.** A `wait_stable(quiet_ms)` tool (termlens,
   `ht --wait-idle`, tui-test-ghost `stable_ms`) replaces the fixed
   `delay` on `send_keys` and the guesswork before `capture_screen`. It is the
   single most common cause of flaky agent runs and costs one loop over the
   buffer.
2. **Find text, return coordinates.** A `find_text(pattern)` returning row and
   column spans (tui-test's locators, termlens's `find_all`) turns
   `assert_at_position` from "the caller guesses the position" into "the
   caller asserts what it found".
3. **Expose cell styles.** pyte and vt10x both carry fg, bg, bold and reverse
   per cell; a `get_cell(row, col)` or a styled `capture_screen` lets an agent
   verify a selected item or an error colour (termless, tui-test-ghost
   `tui_cell`, testty's recipes).
4. **Record the tool calls, replay as a test.** tui-test-ghost's JSONL
   recording and replay converts an agent's exploratory session into a
   deterministic pytest case with no extra authoring. The pytest plugin
   already has the engine for the replay side.
5. **Golden screen snapshots with grid masking.** A `snapshot(name)` that
   compares the buffer text to a stored file, with termlens-style cell masks
   for clocks and PIDs, gives the pytest plugin a regression story and the
   MCP server a one-call assertion.
6. **Answer capability queries.** Replying to `CSI 6n`, DA1 and `DECRQM`
   (termlens, termwright, testty) stops capability-probing apps from stalling
   on launch. Small code, removes a class of mysterious timeouts.
7. **Region on every read.** A `region` parameter on `capture_screen` and the
   assertions (tui-test-ghost) keeps screen text sent to the model small
   without a second call.
8. **Resize.** `resize(cols, rows)` with `SIGWINCH` (most tools) tests the
   layout path that in-process frameworks cannot reach.
9. **Default invariants.** Bombadil's zero-config properties, "exited zero" and
   "never printed a replacement character", are cheap checks the registry
   could report on every `close_session`.
10. **An agent skill file.** A `SKILL.md` describing when to use which mode and
    how to wait (the part `ht` says agents get wrong) complements the MCP
    schema for clients that load skills.
11. **Screenshots.** SVG rendering of the buffer (termscope, termlens) gives a
    human a picture of what the agent saw. Useful, but the text grid already
    serves the model.
12. **Property-based exploration.** Random action generation over the existing
    tools is possible from the harness side today; shrinking and temporal
    properties are Bombadil's whole product and out of scope for this server.
