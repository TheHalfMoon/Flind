# F3 Wave 8 — isolate inherited Node CLI analytics env

## Risk and fix

Flind's Rust CLI embedded a Node API CLI and automatically supplied a
source-provider analytics host and build-time token, even where the user
had not configured any external analytics service. It also propagated an
invocation identifier intended to join Rust and Node telemetry.

This wave removes the inherited analytics URL and build-time analytics-token
injection. The Node child now explicitly excludes these inherited environment
variables, even when they appear in the parent's environment:

- `POSTHOG_ANALYTICS_API_KEY`
- `POSTHOG_ANALYTICS_HOST`
- `POSTHOG_CLI_INVOCATION_ID`

User-scoped API credentials (`POSTHOG_CLI_API_KEY`, project ID and host)
remain available so ordinary authenticated CLI operations are not removed.
Renaming those older protocol environment variables requires independent
API/bundle migration and end-to-end tests.

## Tests and residual risks

- Python static regression checks protect the source and credential-injection
  contract.
- Rust unit test validates the actual `std::process::Command` child
  environment edits, including preservation of a user API key.
- `rustfmt --check` validates formatting.
- Full Cargo compile/test requires the original CLI dependency set, missing
  from the current offline Cargo cache; this source change alone does NOT
  qualify the actual Node bundle, which may contain other telemetry defaults.

**Critical:** this is an analytics-env boundary, not a guarantee that no
network request leaves a system. The Node JS bundle, Rust-side telemetry,
inherited API hosts, updater artifacts and real DNS/HTTP egress still require
runtime tests on supported OSes. Release remains **NO-GO**, private, no
deployment.
