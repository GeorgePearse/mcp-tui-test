// mcp-tui-test (Go): MCP server for testing Terminal User Interfaces.
// Implements the same tool contract as the Python package — same tool names,
// same structured result shapes — as a single static binary.
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/GeorgePearse/mcp-tui-test/go/internal/tui"
)

var registry *tui.Registry

func envInt(name string, def int) int {
	if v := os.Getenv(name); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

// ---- result shapes (mirror mcp_tui_test/server.py TypedDicts) ----

type LaunchResult struct {
	Success   bool   `json:"success"`
	SessionID string `json:"session_id"`
	Command   string `json:"command"`
	Width     int    `json:"width"`
	Height    int    `json:"height"`
	Mode      string `json:"mode"`
	Error     string `json:"error,omitempty"`
}

type ActionResult struct {
	Success   bool   `json:"success"`
	SessionID string `json:"session_id"`
	Error     string `json:"error,omitempty"`
}

type ScreenResult struct {
	Success   bool   `json:"success"`
	SessionID string `json:"session_id"`
	Mode      string `json:"mode"`
	Screen    string `json:"screen"`
	Error     string `json:"error,omitempty"`
}

type ExpectResult struct {
	Success   bool   `json:"success"`
	SessionID string `json:"session_id"`
	Pattern   string `json:"pattern"`
	Outcome   string `json:"outcome"` // found | timeout | eof | error
	Error     string `json:"error,omitempty"`
}

type AssertResult struct {
	Success       bool   `json:"success"`
	Passed        bool   `json:"passed"`
	SessionID     string `json:"session_id"`
	Expected      string `json:"expected"`
	Found         string `json:"found,omitempty"`
	ScreenExcerpt string `json:"screen_excerpt,omitempty"`
	Error         string `json:"error,omitempty"`
}

type CursorResult struct {
	Success   bool   `json:"success"`
	SessionID string `json:"session_id"`
	Row       int    `json:"row"`
	Col       int    `json:"col"`
	Error     string `json:"error,omitempty"`
}

type RegionResult struct {
	Success   bool   `json:"success"`
	SessionID string `json:"session_id"`
	Text      string `json:"text"`
	Error     string `json:"error,omitempty"`
}

type SessionInfo struct {
	SessionID string `json:"session_id"`
	Mode      string `json:"mode"`
	Command   string `json:"command"`
	Alive     bool   `json:"alive"`
}

type SessionList struct {
	Success  bool              `json:"success"`
	Sessions []SessionInfo     `json:"sessions"`
	Reaped   map[string]string `json:"reaped"`
}

// ---- tool inputs ----

type LaunchIn struct {
	Command    string `json:"command" jsonschema:"the command to launch"`
	SessionID  string `json:"session_id,omitempty" jsonschema:"unique identifier for this session"`
	Timeout    int    `json:"timeout,omitempty" jsonschema:"default expect timeout in seconds"`
	Dimensions string `json:"dimensions,omitempty" jsonschema:"terminal dimensions as WIDTHxHEIGHT"`
	Mode       string `json:"mode,omitempty" jsonschema:"stream for CLI tools, buffer for full TUIs"`
}

type KeysIn struct {
	Keys      string  `json:"keys" jsonschema:"keys to send; escapes like \\n \\t \\x1b decoded unless raw"`
	SessionID string  `json:"session_id,omitempty"`
	Delay     float64 `json:"delay,omitempty"`
	Raw       bool    `json:"raw,omitempty"`
}

type CtrlIn struct {
	Key       string `json:"key" jsonschema:"letter to combine with Ctrl, e.g. c"`
	SessionID string `json:"session_id,omitempty"`
}

type CaptureIn struct {
	SessionID   string `json:"session_id,omitempty"`
	IncludeANSI bool   `json:"include_ansi,omitempty"`
	UseBuffer   *bool  `json:"use_buffer,omitempty"`
}

type ExpectIn struct {
	Pattern   string `json:"pattern" jsonschema:"regex or text to wait for"`
	SessionID string `json:"session_id,omitempty"`
	Timeout   int    `json:"timeout,omitempty"`
}

type AssertIn struct {
	Text      string `json:"text" jsonschema:"text that must be on screen"`
	SessionID string `json:"session_id,omitempty"`
	UseBuffer *bool  `json:"use_buffer,omitempty"`
}

type AssertPosIn struct {
	Text      string `json:"text"`
	Row       int    `json:"row"`
	Col       int    `json:"col"`
	SessionID string `json:"session_id,omitempty"`
}

type SessionIn struct {
	SessionID string `json:"session_id,omitempty"`
}

type RegionIn struct {
	RowStart  int    `json:"row_start"`
	RowEnd    int    `json:"row_end"`
	ColStart  int    `json:"col_start,omitempty"`
	ColEnd    *int   `json:"col_end,omitempty"`
	SessionID string `json:"session_id,omitempty"`
}

type LineIn struct {
	Row       int    `json:"row"`
	SessionID string `json:"session_id,omitempty"`
}

type EmptyIn struct{}

func sid(s string) string {
	if s == "" {
		return "default"
	}
	return s
}

func noSession(id string) string { return fmt.Sprintf("no active session: %s", id) }

// ---- handlers ----

func launchTUI(_ context.Context, _ *mcp.CallToolRequest, in LaunchIn) (*mcp.CallToolResult, LaunchResult, error) {
	id := sid(in.SessionID)
	mode := in.Mode
	if mode == "" {
		mode = "stream"
	}
	dims := in.Dimensions
	if dims == "" {
		dims = "80x24"
	}
	parts := strings.SplitN(strings.ToLower(dims), "x", 2)
	fail := func(err string) (*mcp.CallToolResult, LaunchResult, error) {
		return nil, LaunchResult{SessionID: id, Command: in.Command, Mode: mode, Error: err}, nil
	}
	if len(parts) != 2 {
		return fail(fmt.Sprintf("invalid dimensions %q", dims))
	}
	w, err1 := strconv.Atoi(parts[0])
	h, err2 := strconv.Atoi(parts[1])
	if err1 != nil || err2 != nil || w <= 0 || h <= 0 {
		return fail(fmt.Sprintf("invalid dimensions %q", dims))
	}
	if _, err := registry.Launch(in.Command, id, mode, w, h); err != nil {
		return fail(err.Error())
	}
	return nil, LaunchResult{Success: true, SessionID: id, Command: in.Command, Width: w, Height: h, Mode: mode}, nil
}

func sendKeys(_ context.Context, _ *mcp.CallToolRequest, in KeysIn) (*mcp.CallToolResult, ActionResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, ActionResult{SessionID: id, Error: noSession(id)}, nil
	}
	keys := in.Keys
	if !in.Raw {
		keys = tui.DecodeKeys(keys)
	}
	if err := s.Send(keys); err != nil {
		return nil, ActionResult{SessionID: id, Error: err.Error()}, nil
	}
	if in.Delay > 0.1 {
		time.Sleep(time.Duration((in.Delay - 0.1) * float64(time.Second)))
	}
	return nil, ActionResult{Success: true, SessionID: id}, nil
}

func sendCtrl(_ context.Context, _ *mcp.CallToolRequest, in CtrlIn) (*mcp.CallToolResult, ActionResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, ActionResult{SessionID: id, Error: noSession(id)}, nil
	}
	if len(in.Key) != 1 {
		return nil, ActionResult{SessionID: id, Error: fmt.Sprintf("key must be a single letter, got %q", in.Key)}, nil
	}
	c := strings.ToLower(in.Key)[0]
	if c < 'a' || c > 'z' {
		return nil, ActionResult{SessionID: id, Error: fmt.Sprintf("key must be a-z, got %q", in.Key)}, nil
	}
	if err := s.Send(string(rune(c - 'a' + 1))); err != nil {
		return nil, ActionResult{SessionID: id, Error: err.Error()}, nil
	}
	return nil, ActionResult{Success: true, SessionID: id}, nil
}

func captureScreen(_ context.Context, _ *mcp.CallToolRequest, in CaptureIn) (*mcp.CallToolResult, ScreenResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, ScreenResult{SessionID: id, Error: noSession(id)}, nil
	}
	useBuffer := s.Mode == "buffer"
	if in.UseBuffer != nil {
		useBuffer = *in.UseBuffer
	}
	if useBuffer && s.Mode == "buffer" {
		out, err := s.BufferDisplay()
		if err != nil {
			return nil, ScreenResult{SessionID: id, Error: err.Error()}, nil
		}
		return nil, ScreenResult{Success: true, SessionID: id, Mode: "buffer", Screen: out}, nil
	}
	return nil, ScreenResult{Success: true, SessionID: id, Mode: "stream", Screen: s.StreamOutput(in.IncludeANSI)}, nil
}

func expectText(_ context.Context, _ *mcp.CallToolRequest, in ExpectIn) (*mcp.CallToolResult, ExpectResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, ExpectResult{SessionID: id, Pattern: in.Pattern, Outcome: "error", Error: noSession(id)}, nil
	}
	timeout := in.Timeout
	if timeout <= 0 {
		timeout = 10
	}
	outcome, err := s.Expect(in.Pattern, time.Duration(timeout)*time.Second)
	if err != nil {
		return nil, ExpectResult{SessionID: id, Pattern: in.Pattern, Outcome: "error", Error: err.Error()}, nil
	}
	return nil, ExpectResult{Success: outcome == "found", SessionID: id, Pattern: in.Pattern, Outcome: outcome}, nil
}

func assertContains(_ context.Context, _ *mcp.CallToolRequest, in AssertIn) (*mcp.CallToolResult, AssertResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, AssertResult{SessionID: id, Expected: in.Text, Error: noSession(id)}, nil
	}
	useBuffer := s.Mode == "buffer"
	if in.UseBuffer != nil {
		useBuffer = *in.UseBuffer
	}
	var out string
	if useBuffer && s.Mode == "buffer" {
		var err error
		if out, err = s.BufferDisplay(); err != nil {
			return nil, AssertResult{SessionID: id, Expected: in.Text, Error: err.Error()}, nil
		}
	} else {
		out = s.StreamOutput(false)
	}
	res := AssertResult{Success: true, SessionID: id, Expected: in.Text, Passed: strings.Contains(out, in.Text)}
	if res.Passed {
		res.Found = in.Text
	} else {
		if len(out) > 800 {
			out = out[len(out)-800:]
		}
		res.ScreenExcerpt = out
	}
	return nil, res, nil
}

func assertAtPosition(_ context.Context, _ *mcp.CallToolRequest, in AssertPosIn) (*mcp.CallToolResult, AssertResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, AssertResult{SessionID: id, Expected: in.Text, Error: noSession(id)}, nil
	}
	var actual strings.Builder
	for i := range []rune(in.Text) {
		ch, err := s.CharAt(in.Row, in.Col+i)
		if err != nil {
			return nil, AssertResult{SessionID: id, Expected: in.Text, Error: err.Error()}, nil
		}
		actual.WriteString(ch)
	}
	found := strings.TrimSpace(actual.String())
	return nil, AssertResult{
		Success: true, SessionID: id, Expected: in.Text, Found: found,
		Passed: found == strings.TrimSpace(in.Text),
	}, nil
}

func getCursorPosition(_ context.Context, _ *mcp.CallToolRequest, in SessionIn) (*mcp.CallToolResult, CursorResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, CursorResult{SessionID: id, Row: -1, Col: -1, Error: noSession(id)}, nil
	}
	row, col, err := s.CursorPos()
	if err != nil {
		return nil, CursorResult{SessionID: id, Row: -1, Col: -1, Error: err.Error()}, nil
	}
	return nil, CursorResult{Success: true, SessionID: id, Row: row, Col: col}, nil
}

func getScreenRegion(_ context.Context, _ *mcp.CallToolRequest, in RegionIn) (*mcp.CallToolResult, RegionResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, RegionResult{SessionID: id, Error: noSession(id)}, nil
	}
	colEnd := s.Cols
	if in.ColEnd != nil {
		colEnd = *in.ColEnd
	}
	var lines []string
	for row := in.RowStart; row < in.RowEnd; row++ {
		line, err := s.Line(row)
		if err != nil {
			return nil, RegionResult{SessionID: id, Error: err.Error()}, nil
		}
		if in.ColStart < len(line) {
			end := colEnd
			if end > len(line) {
				end = len(line)
			}
			line = line[in.ColStart:end]
		} else {
			line = ""
		}
		lines = append(lines, line)
	}
	return nil, RegionResult{Success: true, SessionID: id, Text: strings.Join(lines, "\n")}, nil
}

func getLine(_ context.Context, _ *mcp.CallToolRequest, in LineIn) (*mcp.CallToolResult, RegionResult, error) {
	id := sid(in.SessionID)
	s, ok := registry.Get(id)
	if !ok {
		return nil, RegionResult{SessionID: id, Error: noSession(id)}, nil
	}
	line, err := s.Line(in.Row)
	if err != nil {
		return nil, RegionResult{SessionID: id, Error: err.Error()}, nil
	}
	return nil, RegionResult{Success: true, SessionID: id, Text: line}, nil
}

func closeSession(_ context.Context, _ *mcp.CallToolRequest, in SessionIn) (*mcp.CallToolResult, ActionResult, error) {
	id := sid(in.SessionID)
	if !registry.Close(id) {
		return nil, ActionResult{SessionID: id, Error: noSession(id)}, nil
	}
	return nil, ActionResult{Success: true, SessionID: id}, nil
}

func listSessions(_ context.Context, _ *mcp.CallToolRequest, _ EmptyIn) (*mcp.CallToolResult, SessionList, error) {
	reaped := registry.Reap()
	out := SessionList{Success: true, Sessions: []SessionInfo{}, Reaped: reaped}
	for id, s := range registry.List() {
		out.Sessions = append(out.Sessions, SessionInfo{SessionID: id, Mode: s.Mode, Command: s.Command, Alive: s.IsAlive()})
	}
	return nil, out, nil
}

func screenResource(_ context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
	uri := req.Params.URI
	id := strings.TrimSuffix(strings.TrimPrefix(uri, "tui://"), "/screen")
	text := fmt.Sprintf("(no active session: %s)", id)
	if s, ok := registry.Get(id); ok {
		text = s.ScreenText()
	}
	return &mcp.ReadResourceResult{
		Contents: []*mcp.ResourceContents{{URI: uri, MIMEType: "text/plain", Text: text}},
	}, nil
}

func main() {
	registry = tui.NewRegistry(
		envInt("MCP_TUI_MAX_SESSIONS", 8),
		time.Duration(envInt("MCP_TUI_SESSION_TTL_S", 900))*time.Second,
	)
	defer registry.CloseAll()

	server := mcp.NewServer(&mcp.Implementation{Name: "tui-test", Version: "0.3.0"}, nil)

	mcp.AddTool(server, &mcp.Tool{Name: "launch_tui", Description: "Launch a TUI application for testing."}, launchTUI)
	mcp.AddTool(server, &mcp.Tool{Name: "send_keys", Description: "Send keyboard input. Escapes like \\n, \\t, \\x1b are decoded unless raw=true."}, sendKeys)
	mcp.AddTool(server, &mcp.Tool{Name: "send_ctrl", Description: "Send a Ctrl+<key> combination (e.g. key='c' sends Ctrl-C)."}, sendCtrl)
	mcp.AddTool(server, &mcp.Tool{Name: "capture_screen", Description: "Capture the current screen (buffer display in buffer mode, cleaned stream otherwise)."}, captureScreen)
	mcp.AddTool(server, &mcp.Tool{Name: "expect_text", Description: "Wait until a regex/text pattern appears in the output (or timeout/EOF)."}, expectText)
	mcp.AddTool(server, &mcp.Tool{Name: "assert_contains", Description: "Assert the current screen contains text; on failure includes a screen excerpt."}, assertContains)
	mcp.AddTool(server, &mcp.Tool{Name: "assert_at_position", Description: "Assert text appears at (row, col) — buffer mode only."}, assertAtPosition)
	mcp.AddTool(server, &mcp.Tool{Name: "get_cursor_position", Description: "Current cursor (row, col) — buffer mode only."}, getCursorPosition)
	mcp.AddTool(server, &mcp.Tool{Name: "get_screen_region", Description: "Extract a rectangular screen region — buffer mode only."}, getScreenRegion)
	mcp.AddTool(server, &mcp.Tool{Name: "get_line", Description: "Get one screen-buffer line — buffer mode only."}, getLine)
	mcp.AddTool(server, &mcp.Tool{Name: "close_session", Description: "Close a session and reap its process."}, closeSession)
	mcp.AddTool(server, &mcp.Tool{Name: "list_sessions", Description: "List active sessions (dead/expired ones are reaped and reported)."}, listSessions)

	server.AddResourceTemplate(
		&mcp.ResourceTemplate{
			URITemplate: "tui://{session_id}/screen",
			Name:        "screen",
			Description: "The session's current screen as plain text.",
			MIMEType:    "text/plain",
		},
		screenResource,
	)

	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatal(err)
	}
}
