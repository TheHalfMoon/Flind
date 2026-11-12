package sse

import (
    "context"
    "net/http"
    "net/http/httptest"
    "testing"
)

func TestBearerTokenIsNeverForwardedThroughStatsRedirect(t *testing.T) {
    received := false
    sink := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Header.Get("Authorization") != "" {
            received = true
        }
        w.WriteHeader(http.StatusOK)
    }))
    defer sink.Close()
    origin := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Header.Get("Authorization") != "Bearer synthetic" {
            t.Errorf("original request should carry synthetic test token")
        }
        http.Redirect(w, r, sink.URL+"/unexpected", http.StatusFound)
    }))
    defer origin.Close()

    client := NewClient(origin.URL, "synthetic", "", "", false)
    msg := FetchStats(PollStatsMsg{SSEClient: client, Ctx: context.Background()})()
    if _, ok := msg.(StatsErrorMsg); !ok {
        t.Fatalf("redirect must not be treated as successful stats response: %T", msg)
    }
    if received {
        t.Fatal("bearer token reached a redirected recipient")
    }
}

func TestBearerTokenIsNeverForwardedThroughEventStreamRedirect(t *testing.T) {
    received := false
    sink := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Header.Get("Authorization") != "" {
            received = true
        }
        w.WriteHeader(http.StatusOK)
    }))
    defer sink.Close()
    origin := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        http.Redirect(w, r, sink.URL+"/unexpected", http.StatusFound)
    }))
    defer origin.Close()

    client := NewClient(origin.URL, "synthetic", "", "", false)
    stream := &Stream{client: client, ctx: context.Background()}
    if err := stream.connectAndStream(); err == nil {
        t.Fatal("SSE redirect must fail closed")
    }
    if received {
        t.Fatal("bearer token reached a redirected event-stream recipient")
    }
}
