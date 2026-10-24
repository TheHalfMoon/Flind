# F3 Wave 10 — Flind CLI login requires an explicit host

## Source risk

The copied CLI login flow offered US/EU selections that silently targeted
provider-owned authentication endpoints. The manual-login form prepopulated
that same external cloud URL, and Token::get_host returned the provider's
cloud as a fallback whenever stored credentials omitted an explicit host.

This is unsuitable for an independently operated Flind distribution.

## Implementation

- Remove hardcoded external region selections from the CLI login flow.
- Device-code OAuth login now needs an explicitly chosen host override.
  When no override is supplied, the CLI presents manual Flind login rather
  than starting an authorization handshake with another company.
- Manual login asks for the Flind instance URL without an inherited default.
  Existing host validation still applies. Tokens, environment and project ID
  inputs are preserved.
- A missing stored host produces an empty Token::get_host value rather than
  silently substituting a remote cloud host. The CLI API context already
  rejects missing hosts with a readable Flind configuration error.
- Tests include explicit localhost and first-party host handling, and
  legacy host fixture replaced by a Flind sample URL.

## Caveats

CLI binaries and command recommendations still have inherited package
identity strings. Changing executable filenames and compatibility env
variables must be handled together with packaging, API contracts and
cross-platform integration. OAuth device-code endpoints and browser
verification links have NOT been qualified against a real Flind issuer.

Source-level Python tests and rustfmt are available in this wave. Actual
Cargo project tests, full login E2E and DNS/HTTP egress tracing must pass
before an independent Flind CLI can be released. No publication; **NO-GO**.

## macOS Rust test evidence, 2026-10-24

The CLI's full `cargo test --all-targets --offline --locked` suite
passed **337/337** after dependency retrieval and the shared CLI proxy
test fix. The host-selection unit cases passed. Real Flind OAuth
issuer/browser journeys are still unqualified.
