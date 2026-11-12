package auth

import (
	"fmt"
	"net"
	"net/url"
	"strings"
)

// validatedBaseHost accepts only explicit HTTPS endpoints or local loopback HTTP.
// Inherited upstream cloud hosts are never authorized Flind token recipients.
func validatedBaseHost(raw string) (string, error) {
	host := strings.TrimRight(strings.TrimSpace(raw), "/")
	u, err := url.Parse(host)
	if err != nil || u.Host == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || (u.Path != "" && u.Path != "/") {
		return "", fmt.Errorf("invalid Flind host; provide an absolute origin")
	}
	name := strings.ToLower(u.Hostname())
	if name == "posthog.com" || strings.HasSuffix(name, ".posthog.com") ||
		name == "posthog.dev" || strings.HasSuffix(name, ".posthog.dev") {
		return "", fmt.Errorf("inherited upstream host is not a Flind endpoint")
	}
	if u.Scheme != "https" && !(u.Scheme == "http" && isLoopback(name)) {
		return "", fmt.Errorf("Flind host must use HTTPS, or HTTP on loopback")
	}
	return host, nil
}

 // Reported callback hosts are untrusted query parameters. Never transfer a
 // browser-issued credential to an origin other than the Flind origin opened.
func validatedCallbackHost(requestedHost, callbackHost string) (string, error) {
    requested, err := validatedBaseHost(requestedHost)
    if err != nil {
        return "", err
    }
    if callbackHost == "" {
        return requested, nil
    }
    actual, err := validatedBaseHost(callbackHost)
    if err != nil {
        return "", err
    }
    expectedURL, _ := url.Parse(requested)
    actualURL, _ := url.Parse(actual)
    if expectedURL.Scheme != actualURL.Scheme || !strings.EqualFold(expectedURL.Host, actualURL.Host) {
        return "", fmt.Errorf("authorization callback reported an unexpected Flind origin")
    }
    return requested, nil
}

func isLoopback(hostname string) bool {
	if hostname == "localhost" {
		return true
	}
	ip := net.ParseIP(hostname)
	return ip != nil && ip.IsLoopback()
}

// DeriveStreamHost only derives a local development endpoint. Remote Flind
// installations must explicitly provide their own --livestream-host.
func DeriveStreamHost(appHost string) string {
	host, err := validatedBaseHost(appHost)
	if err != nil {
		return ""
	}
	u, err := url.Parse(host)
	if err != nil || !isLoopback(strings.ToLower(u.Hostname())) {
		return ""
	}
	return "http://localhost:8010"
}

func resolveStreamHost(appHost, override string) (string, error) {
	if override == "" {
		override = DeriveStreamHost(appHost)
	}
	if override == "" {
		return "", fmt.Errorf("specify an owned Flind --livestream-host for this remote environment")
	}
	return validatedBaseHost(override)
}
