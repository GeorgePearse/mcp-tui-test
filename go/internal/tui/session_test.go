package tui

import (
	"strings"
	"testing"
	"time"
)

func TestDecodeKeys(t *testing.T) {
	cases := map[string]string{
		"hello\\n":   "hello\n",
		"\\x1b[A":    "\x1b[A",
		"naïve ✓":    "naïve ✓",
		"mixed ✓\\t": "mixed ✓\t",
		"a\\\\b":     "a\\b",
	}
	for in, want := range cases {
		if got := DecodeKeys(in); got != want {
			t.Errorf("DecodeKeys(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestStreamSessionEcho(t *testing.T) {
	s, err := NewSession(`read line; echo "got:$line"`, "stream", 80, 24, 0)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	if err := s.Send("hello world\n"); err != nil {
		t.Fatal(err)
	}
	outcome, err := s.Expect("got:hello world", 5*time.Second)
	if err != nil || outcome != "found" {
		t.Fatalf("expect: outcome=%s err=%v output=%q", outcome, err, s.StreamOutput(false))
	}
	if !strings.Contains(s.StreamOutput(false), "got:hello world") {
		t.Fatalf("stream output missing echo: %q", s.StreamOutput(false))
	}
}

func TestBufferSessionPositions(t *testing.T) {
	// Clear screen, move to row 3 col 5 (1-indexed), print MARK, then block.
	s, err := NewSession(`printf '\033[2J\033[3;5HMARK'; read x`, "buffer", 40, 10, 0)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if disp, _ := s.BufferDisplay(); strings.Contains(disp, "MARK") {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
	disp, err := s.BufferDisplay()
	if err != nil || !strings.Contains(disp, "MARK") {
		t.Fatalf("display missing MARK: err=%v disp=%q", err, disp)
	}
	if ch, _ := s.CharAt(2, 4); ch != "M" {
		t.Errorf("CharAt(2,4) = %q, want M", ch)
	}
	if line, _ := s.Line(2); strings.TrimSpace(line) != "MARK" {
		t.Errorf("Line(2) = %q, want MARK", line)
	}
	if row, col, err := s.CursorPos(); err != nil || row < 0 || col < 0 {
		t.Errorf("CursorPos = (%d,%d) err=%v", row, col, err)
	}
}

func TestExpectTimeoutAndEOF(t *testing.T) {
	s, err := NewSession("read x", "stream", 80, 24, 0)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	if outcome, _ := s.Expect("never-appears", 1*time.Second); outcome != "timeout" {
		t.Fatalf("want timeout, got %s", outcome)
	}

	s2, err := NewSession("true", "stream", 80, 24, 0)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	if outcome, _ := s2.Expect("never-appears", 5*time.Second); outcome != "eof" {
		t.Fatalf("want eof, got %s", outcome)
	}
}

func TestRegistryCapAndReap(t *testing.T) {
	r := NewRegistry(2, 0)
	defer r.CloseAll()
	if _, err := r.Launch("read x", "a", "stream", 80, 24); err != nil {
		t.Fatal(err)
	}
	if _, err := r.Launch("read x", "b", "stream", 80, 24); err != nil {
		t.Fatal(err)
	}
	if _, err := r.Launch("read x", "c", "stream", 80, 24); err == nil {
		t.Fatal("expected session cap error")
	}
	// Kill one; registry should reap it and admit a new session.
	sa, _ := r.Get("a")
	sa.Close()
	time.Sleep(300 * time.Millisecond)
	reaped := r.Reap()
	if _, ok := reaped["a"]; !ok {
		t.Fatalf("expected 'a' reaped, got %v", reaped)
	}
	if _, err := r.Launch("read x", "c", "stream", 80, 24); err != nil {
		t.Fatalf("launch after reap: %v", err)
	}
}

func TestRegistryTTL(t *testing.T) {
	r := NewRegistry(4, 200*time.Millisecond)
	defer r.CloseAll()
	if _, err := r.Launch("read x", "short", "stream", 80, 24); err != nil {
		t.Fatal(err)
	}
	time.Sleep(400 * time.Millisecond)
	if _, ok := r.Get("short"); ok {
		t.Fatal("expected TTL-expired session to be gone")
	}
}
