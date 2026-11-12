package auth

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestDeriveStreamHost(t *testing.T) {
	tests := []struct {
		name, appHost, expected string
	}{
		{"local dev", "http://localhost:8000", "http://localhost:8010"},
		{"local IPv4", "http://127.0.0.1:8000", "http://localhost:8010"},
		{"local IPv6", "http://[::1]:8000", "http://localhost:8010"},
		{"upstream US", "https://us.posthog.com", ""},
		{"upstream EU", "https://eu.posthog.com", ""},
		{"upstream app", "https://app.posthog.com/", ""},
		{"upstream dev", "https://app.dev.posthog.dev", ""},
		{"remote Flind requires explicit stream", "https://flind.example", ""},
		{"unknown host", "https://custom.example.com", ""},
		{"lookalike loopback", "http://localhost.evil:8000", ""},
		{"malformed", "not-a-url", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.expected, DeriveStreamHost(tt.appHost))
		})
	}
}

func TestResolveStreamHostRequiresOwnedExplicitRemoteEndpoint(t *testing.T) {
	for _, bad := range []string{
		"https://live.us.posthog.com", "https://live.eu.posthog.com",
		"https://live.dev.posthog.dev", "http://public.example", "https://user:pass@flind.example",
		"https://flind.example/path", "javascript:alert(1)",
	} {
		_, err := resolveStreamHost("https://flind.example", bad)
		assert.Error(t, err, bad)
	}
	host, err := resolveStreamHost("https://flind.example", "https://live.flind.example/")
	assert.NoError(t, err)
	assert.Equal(t, "https://live.flind.example", host)
	_, err = resolveStreamHost("https://flind.example", "")
	assert.ErrorContains(t, err, "--livestream-host")
}

func TestDirectTokenAuthenticationFailsClosedWithoutHostOrForUpstream(t *testing.T) {
	for _, opts := range []Options{
		{Token: "synthetic"},
		{Token: "synthetic", Host: "https://app.posthog.com", LivestreamHost: "https://live.flind.example"},
		{Token: "synthetic", Host: "https://flind.example", LivestreamHost: "https://live.us.posthog.com"},
		{Token: "synthetic", Host: "https://flind.example"},
	} {
		_, err := Authenticate(opts)
		assert.Error(t, err)
	}
	creds, err := Authenticate(Options{
		Token: "synthetic",
		Host: "https://flind.example",
		LivestreamHost: "https://live.flind.example",
	})
	assert.NoError(t, err)
	assert.Equal(t, "https://live.flind.example", creds.LivestreamHost)
	assert.True(t, strings.HasPrefix(creds.Host, "https://"))
}
