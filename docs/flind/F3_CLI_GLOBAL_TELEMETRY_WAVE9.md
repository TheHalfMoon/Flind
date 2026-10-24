# F3 Wave 9 — stop inherited CLI global analytics and implicit API host

## Scope and risk

The imported Rust CLI initialized the provider's global analytics client
with an API token compiled into the binary, used it to emit command/project
usage and exception events, and flushed events before exit. This is not
appropriate as default behavior in an independently distributed Flind CLI.

A separate API context path silently fell back to the inherited cloud
ingestion host when neither a CLI host override nor saved credentials had
a host. This could send authenticated requests to a provider the user did
not select.

## Implemented

- The main CLI entrypoint no longer initializes or flushes an inherited
  global analytics client.
- Delete the code that initializes `posthog_rs::init_global` with the
  embedded build-time `POSTHOG_API_TOKEN` and its event enrichment.
- No default cloud ingestion endpoint is supplied for the normal user
  API client. `init_context` now requires an explicitly supplied override
  or a stored host, otherwise returns a descriptive configuration error.
- Historical configuration and user API flow are preserved for explicitly
  supplied Flind instance and localhost hosts. No invented cloud URL.

## Evidence

Python source regression tests cover the missing SDK initializer, missing
compiled-in analytics token, explicit host resolution and Rust test cases.
Rustfmt and the larger existing Flind Python source regression suite should
be run as quality gates.

**Caveat:** other CLI source functions still construct and invoke SDK
capture calls, but no global inherited analytics client is initialized by
this CLI entrypoint. The runtime behavior of those calls without a global
client and full Rust compilation need testing before release; this change
does not claim complete CLI network isolation.

Other historical host defaults in login, generated SDKs, products and
backend need separate tests. End-to-end network capture, build, and OS
packaging remain **NO-GO**. Repository private; no public deployment.

## macOS Rust test evidence, 2026-10-24

After fetching public Cargo crates and fixing the related CLI proxy test,
the complete CLI `cargo test --all-targets --offline --locked` suite
passed **337/337** tests. This supersedes the prior local-cache blocker
for macOS Rust test execution; it does **not** establish runtime DNS/HTTP
egress isolation, Windows/Linux packaging, or production readiness.
