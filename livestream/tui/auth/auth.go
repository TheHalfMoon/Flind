package auth

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/pkg/browser"
	"github.com/posthog/posthog/livestream/tui/config"
)

type Options struct {
	Token          string
	Host           string
	LivestreamHost string
}

func Authenticate(opts Options) (*config.Credentials, error) {
	host := strings.TrimRight(strings.TrimSpace(opts.Host), "/")
	if host != "" {
		if _, err := validatedBaseHost(host); err != nil {
			return nil, err
		}
	}

	// Direct token flags must specify the Flind deployment explicitly.
	if opts.Token != "" {
		if host == "" {
			return nil, fmt.Errorf("pass --host for your Flind deployment when using --token")
		}
		streamHost, err := resolveStreamHost(host, opts.LivestreamHost)
		if err != nil {
			return nil, err
		}
		return &config.Credentials{
			Host:           host,
			LivestreamHost: streamHost,
			Token:          opts.Token,
			ExpiresAt:      time.Now().Add(7 * 24 * time.Hour),
		}, nil
	}

	// Only read the Flind-owned cache, never reuse credentials at the old donor path.
	cfg := config.Load()
	if cfg.Credentials != nil && !cfg.Credentials.IsExpired() {
		creds := cfg.Credentials
		if host != "" && strings.TrimRight(creds.Host, "/") != host {
			// An old token must never follow a changed app host.
			return browserFlow(host, opts.LivestreamHost)
		}
		if host == "" {
			host = creds.Host
		}
		if _, err := validatedBaseHost(host); err != nil {
			return nil, err
		}
		streamHost := opts.LivestreamHost
		if streamHost == "" {
			streamHost = creds.LivestreamHost
		}
		resolved, err := resolveStreamHost(host, streamHost)
		if err != nil {
			return nil, err
		}
		creds.Host, creds.LivestreamHost = host, resolved
		return creds, nil
	}

	if host == "" {
		return nil, fmt.Errorf("pass --host for your Flind deployment; no default third-party host is used")
	}
	return browserFlow(host, opts.LivestreamHost)
}

func browserFlow(host, livestreamHostOverride string) (*config.Credentials, error) {
	if _, err := validatedBaseHost(host); err != nil {
		return nil, err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	port, resultCh, err := StartCallbackServer(ctx)
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s/cli/live?port=%d", host, port)
	fmt.Printf("Opening browser to authorize: %s\n", url)
	if err := browser.OpenURL(url); err != nil {
		fmt.Printf("Could not open browser automatically.\nPlease open this URL manually:\n  %s\n", url)
	}

	fmt.Println("Waiting for authorization...")

	select {
	case result := <-resultCh:
		if result.Err != nil {
			return nil, result.Err
		}

		actualHost, err := validatedCallbackHost(host, result.APIHost)
		if err != nil {
			return nil, err
		}
		streamHost, err := resolveStreamHost(actualHost, livestreamHostOverride)
		if err != nil {
			return nil, err
		}

		creds := &config.Credentials{
			Host:           actualHost,
			LivestreamHost: streamHost,
			Token:          result.Token,
			TeamID:         result.TeamID,
			TeamName:       result.TeamName,
			ExpiresAt:      time.Now().Add(7 * 24 * time.Hour),
		}

		cfg := config.Load()
		cfg.Credentials = creds
		if err := config.Save(cfg); err != nil {
			fmt.Printf("Warning: could not save credentials: %v\n", err)
		}
		return creds, nil
	case <-ctx.Done():
		return nil, fmt.Errorf("authorization timed out")
	}
}
