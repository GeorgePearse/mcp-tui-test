// Package tui is the session engine: a PTY-driven process with optional
// vt10x screen-buffer emulation, plus a registry owning lifecycle (caps,
// TTLs, dead-process reaping). It mirrors mcp_tui_test/core.py.
package tui

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/creack/pty"
	"github.com/hinshun/vt10x"
)

var ansiEscape = regexp.MustCompile(`\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])`)

const transcriptCap = 512 * 1024

// DecodeKeys interprets common backslash escapes (\n, \t, \r, \x1b, \\)
// without touching the rest of the string.
func DecodeKeys(s string) string {
	if !strings.Contains(s, `\`) {
		return s
	}
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		if s[i] != '\\' || i+1 >= len(s) {
			b.WriteByte(s[i])
			continue
		}
		switch s[i+1] {
		case 'n':
			b.WriteByte('\n')
			i++
		case 't':
			b.WriteByte('\t')
			i++
		case 'r':
			b.WriteByte('\r')
			i++
		case '\\':
			b.WriteByte('\\')
			i++
		case 'x':
			if i+3 < len(s) {
				if v, err := strconv.ParseUint(s[i+2:i+4], 16, 8); err == nil {
					b.WriteByte(byte(v))
					i += 3
					continue
				}
			}
			b.WriteByte(s[i])
		default:
			b.WriteByte(s[i])
		}
	}
	return b.String()
}

// Session is one PTY-driven process under test.
type Session struct {
	Command string
	Mode    string // "stream" or "buffer"
	Cols    int
	Rows    int

	mu         sync.Mutex
	cond       *sync.Cond
	cmd        *exec.Cmd
	ptmx       *os.File
	term       vt10x.Terminal
	transcript []byte
	eof        bool
	exited     bool
	closed     bool
	deadline   time.Time
}

// NewSession launches command in a PTY of the given size.
func NewSession(command, mode string, cols, rows int, ttl time.Duration) (*Session, error) {
	if mode != "stream" && mode != "buffer" {
		return nil, fmt.Errorf("mode must be \"stream\" or \"buffer\", got %q", mode)
	}
	cmd := exec.Command("/bin/sh", "-c", command)
	ptmx, err := pty.StartWithSize(cmd, &pty.Winsize{Cols: uint16(cols), Rows: uint16(rows)})
	if err != nil {
		return nil, err
	}
	s := &Session{Command: command, Mode: mode, Cols: cols, Rows: rows, cmd: cmd, ptmx: ptmx}
	s.cond = sync.NewCond(&s.mu)
	if ttl > 0 {
		s.deadline = time.Now().Add(ttl)
	}
	if mode == "buffer" {
		s.term = vt10x.New(vt10x.WithSize(cols, rows))
	}
	go s.readLoop()
	go func() {
		_ = cmd.Wait()
		s.mu.Lock()
		s.exited = true
		s.cond.Broadcast()
		s.mu.Unlock()
	}()
	return s, nil
}

func (s *Session) readLoop() {
	buf := make([]byte, 32*1024)
	for {
		n, err := s.ptmx.Read(buf)
		s.mu.Lock()
		if n > 0 {
			s.transcript = append(s.transcript, buf[:n]...)
			if len(s.transcript) > transcriptCap {
				s.transcript = s.transcript[len(s.transcript)-transcriptCap:]
			}
			if s.term != nil {
				_, _ = s.term.Write(buf[:n])
			}
		}
		if err != nil {
			s.eof = true
			s.cond.Broadcast()
			s.mu.Unlock()
			return
		}
		s.cond.Broadcast()
		s.mu.Unlock()
	}
}

// Send writes keys to the PTY.
func (s *Session) Send(keys string) error {
	s.mu.Lock()
	closed := s.closed
	s.mu.Unlock()
	if closed {
		return fmt.Errorf("session closed")
	}
	_, err := s.ptmx.WriteString(keys)
	time.Sleep(100 * time.Millisecond)
	return err
}

// IsAlive reports whether the child process is still running.
func (s *Session) IsAlive() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return !s.exited && !s.closed
}

// Expired reports whether the session TTL has passed.
func (s *Session) Expired() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return !s.deadline.IsZero() && time.Now().After(s.deadline)
}

// StreamOutput returns the accumulated transcript (ANSI-stripped by default).
func (s *Session) StreamOutput(includeANSI bool) string {
	s.mu.Lock()
	out := string(s.transcript)
	s.mu.Unlock()
	if !includeANSI {
		out = ansiEscape.ReplaceAllString(out, "")
	}
	return out
}

// BufferDisplay returns the rendered screen (buffer mode only).
func (s *Session) BufferDisplay() (string, error) {
	if s.term == nil {
		return "", fmt.Errorf("buffer mode not enabled for this session")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	lines := strings.Split(s.term.String(), "\n")
	for i := range lines {
		lines[i] = strings.TrimRight(lines[i], " ")
	}
	return strings.TrimRight(strings.Join(lines, "\n"), "\n"), nil
}

// Line returns one screen row (buffer mode only).
func (s *Session) Line(row int) (string, error) {
	if s.term == nil {
		return "", fmt.Errorf("buffer mode not enabled for this session")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if row < 0 || row >= s.Rows {
		return "", nil
	}
	var b strings.Builder
	for col := 0; col < s.Cols; col++ {
		g := s.term.Cell(col, row)
		if g.Char == 0 {
			b.WriteByte(' ')
		} else {
			b.WriteRune(g.Char)
		}
	}
	return strings.TrimRight(b.String(), " "), nil
}

// CharAt returns the glyph at (row, col) (buffer mode only).
func (s *Session) CharAt(row, col int) (string, error) {
	if s.term == nil {
		return "", fmt.Errorf("buffer mode not enabled for this session")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if row < 0 || row >= s.Rows || col < 0 || col >= s.Cols {
		return "", nil
	}
	g := s.term.Cell(col, row)
	if g.Char == 0 {
		return " ", nil
	}
	return string(g.Char), nil
}

// CursorPos returns (row, col) of the cursor (buffer mode only).
func (s *Session) CursorPos() (int, int, error) {
	if s.term == nil {
		return -1, -1, fmt.Errorf("buffer mode not enabled for this session")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	c := s.term.Cursor()
	return c.Y, c.X, nil
}

// ScreenText is the best-available textual screen.
func (s *Session) ScreenText() string {
	if s.term != nil {
		if out, err := s.BufferDisplay(); err == nil {
			return out
		}
	}
	return s.StreamOutput(false)
}

// Expect waits until pattern (a regexp) matches the transcript.
// Returns "found", "timeout", or "eof".
func (s *Session) Expect(pattern string, timeout time.Duration) (string, error) {
	re, err := regexp.Compile(pattern)
	if err != nil {
		return "", fmt.Errorf("invalid pattern: %w", err)
	}
	deadline := time.Now().Add(timeout)
	timer := time.AfterFunc(timeout, func() {
		s.mu.Lock()
		s.cond.Broadcast()
		s.mu.Unlock()
	})
	defer timer.Stop()

	s.mu.Lock()
	defer s.mu.Unlock()
	for {
		if re.Match(ansiEscape.ReplaceAll(s.transcript, nil)) {
			return "found", nil
		}
		if s.eof || s.exited {
			return "eof", nil
		}
		if time.Now().After(deadline) {
			return "timeout", nil
		}
		s.cond.Wait()
	}
}

// Close kills the child and releases the PTY.
func (s *Session) Close() {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return
	}
	s.closed = true
	s.mu.Unlock()
	if s.cmd.Process != nil {
		_ = s.cmd.Process.Kill()
	}
	_ = s.ptmx.Close()
}

// Registry owns sessions: cap, TTL reaping, dead-process reaping, close-all.
type Registry struct {
	MaxSessions int
	TTL         time.Duration

	mu       sync.Mutex
	sessions map[string]*Session
}

func NewRegistry(maxSessions int, ttl time.Duration) *Registry {
	return &Registry{MaxSessions: maxSessions, TTL: ttl, sessions: map[string]*Session{}}
}

// Reap removes dead or expired sessions; returns {id: reason}.
func (r *Registry) Reap() map[string]string {
	r.mu.Lock()
	defer r.mu.Unlock()
	reaped := map[string]string{}
	for id, s := range r.sessions {
		var reason string
		switch {
		case !s.IsAlive():
			reason = "process exited"
		case s.Expired():
			reason = "session TTL expired"
		default:
			continue
		}
		s.Close()
		delete(r.sessions, id)
		reaped[id] = reason
	}
	return reaped
}

func (r *Registry) Launch(command, id, mode string, cols, rows int) (*Session, error) {
	r.Reap()
	r.mu.Lock()
	if old, ok := r.sessions[id]; ok {
		old.Close()
		delete(r.sessions, id)
	}
	if len(r.sessions) >= r.MaxSessions {
		r.mu.Unlock()
		return nil, fmt.Errorf("session cap reached (%d); close a session or raise MCP_TUI_MAX_SESSIONS", r.MaxSessions)
	}
	r.mu.Unlock()

	s, err := NewSession(command, mode, cols, rows, r.TTL)
	if err != nil {
		return nil, err
	}
	r.mu.Lock()
	r.sessions[id] = s
	r.mu.Unlock()
	time.Sleep(500 * time.Millisecond) // settle before first capture
	return s, nil
}

func (r *Registry) Get(id string) (*Session, bool) {
	r.Reap()
	r.mu.Lock()
	defer r.mu.Unlock()
	s, ok := r.sessions[id]
	return s, ok
}

func (r *Registry) Close(id string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	s, ok := r.sessions[id]
	if ok {
		s.Close()
		delete(r.sessions, id)
	}
	return ok
}

func (r *Registry) CloseAll() {
	r.mu.Lock()
	defer r.mu.Unlock()
	for id, s := range r.sessions {
		s.Close()
		delete(r.sessions, id)
	}
}

// List returns a stable snapshot of live sessions.
func (r *Registry) List() map[string]*Session {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make(map[string]*Session, len(r.sessions))
	for id, s := range r.sessions {
		out[id] = s
	}
	return out
}
