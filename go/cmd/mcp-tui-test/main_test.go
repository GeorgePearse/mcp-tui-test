package main

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/GeorgePearse/mcp-tui-test/go/internal/tui"
)

func withRegistry(t *testing.T) {
	t.Helper()
	registry = tui.NewRegistry(8, 15*time.Minute)
	t.Cleanup(registry.CloseAll)
}

func TestLaunchExpectCaptureFlow(t *testing.T) {
	withRegistry(t)
	ctx := context.Background()

	_, launch, err := launchTUI(ctx, nil, LaunchIn{Command: `echo READY; read x`, SessionID: "t1"})
	if err != nil || !launch.Success {
		t.Fatalf("launch: %+v err=%v", launch, err)
	}
	if launch.Width != 80 || launch.Height != 24 {
		t.Fatalf("default dims wrong: %+v", launch)
	}

	_, exp, _ := expectText(ctx, nil, ExpectIn{Pattern: "READY", SessionID: "t1", Timeout: 5})
	if !exp.Success || exp.Outcome != "found" {
		t.Fatalf("expect: %+v", exp)
	}

	_, cap_, _ := captureScreen(ctx, nil, CaptureIn{SessionID: "t1"})
	if !cap_.Success || cap_.Mode != "stream" || !strings.Contains(cap_.Screen, "READY") {
		t.Fatalf("capture: %+v", cap_)
	}
}

func TestMissingSessionStructuredError(t *testing.T) {
	withRegistry(t)
	_, res, _ := sendKeys(context.Background(), nil, KeysIn{Keys: "x", SessionID: "nope"})
	if res.Success || !strings.Contains(res.Error, "no active session") {
		t.Fatalf("want structured error, got %+v", res)
	}
}

func TestAssertContainsExcerptOnFailure(t *testing.T) {
	withRegistry(t)
	ctx := context.Background()
	launchTUI(ctx, nil, LaunchIn{Command: `echo alpha beta; read x`, SessionID: "t2"})
	expectText(ctx, nil, ExpectIn{Pattern: "beta", SessionID: "t2", Timeout: 5})
	_, res, _ := assertContains(ctx, nil, AssertIn{Text: "gamma", SessionID: "t2"})
	if !res.Success || res.Passed || res.ScreenExcerpt == "" {
		t.Fatalf("want failed assert with excerpt, got %+v", res)
	}
}

func TestBufferPositionAssert(t *testing.T) {
	withRegistry(t)
	ctx := context.Background()
	_, launch, _ := launchTUI(ctx, nil, LaunchIn{
		Command: `printf '\033[2J\033[1;1HOK'; read x`, SessionID: "t3", Dimensions: "40x10", Mode: "buffer",
	})
	if !launch.Success {
		t.Fatalf("launch: %+v", launch)
	}
	deadline := time.Now().Add(5 * time.Second)
	var res AssertResult
	for time.Now().Before(deadline) {
		_, res, _ = assertAtPosition(ctx, nil, AssertPosIn{Text: "OK", Row: 0, Col: 0, SessionID: "t3"})
		if res.Passed {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
	if !res.Passed {
		t.Fatalf("assert_at_position: %+v", res)
	}
	_, cur, _ := getCursorPosition(ctx, nil, SessionIn{SessionID: "t3"})
	if !cur.Success || cur.Row < 0 {
		t.Fatalf("cursor: %+v", cur)
	}
}

func TestListSessionsReapsDead(t *testing.T) {
	withRegistry(t)
	ctx := context.Background()
	launchTUI(ctx, nil, LaunchIn{Command: "true", SessionID: "dies"})
	time.Sleep(800 * time.Millisecond)
	_, listed, _ := listSessions(ctx, nil, EmptyIn{})
	if !listed.Success {
		t.Fatalf("list: %+v", listed)
	}
	if _, reaped := listed.Reaped["dies"]; !reaped {
		for _, s := range listed.Sessions {
			if s.SessionID == "dies" {
				t.Fatalf("dead session still listed: %+v", listed)
			}
		}
	}
}
