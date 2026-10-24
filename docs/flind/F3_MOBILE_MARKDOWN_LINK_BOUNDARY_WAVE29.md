# Wave 29 — Mobile Markdown reference link isolation

## Observed

The mobile Markdown reference chip parser recognized hardcoded original
provider app, code and marketing domains regardless of Flind configuration.
It could visually elevate unrelated inherited URLs to first-party internal
task, insight or docs references. Wave 28 removed default universal links,
but this separate old host allowlist remained.

## Changes

- Replace hardcoded original vendor allowlists with approved explicitly
  configured Flind appBaseUrl and codeBaseUrl origins.
- Recognize only a matching configured origin. Reject inherited provider
  apex/subdomains, credential-bearing URLs, origin paths/query/fragments,
  insecure remote HTTP and hostname spoofing.
- Support HTTPS self-hosted origins, localhost HTTP in development and one
  shared origin for both app and code routes, distinguishing task/inbox
  from other app routes by path.
- Rename visible fallback chip label to Flind while preserving the old
  TypeScript function/types exported to other source consumers until
  internal compatibility work is separately qualified.
- Vendor marketing and documentation URLs are no longer classified as
  special first-party references; other Markdown URL rendering remains
  unchanged, so full external link handling needs browser verification.

## Verification

- Runtime test executed transpiled real TypeScript parser: 19/19 PASS
  including explicit Flind references, absent config, spoofed hostname,
  local development, shared code/app host and upstream URL rejection.
- TypeScript source and updated behavioral Vitest test parsed without syntax
  errors.
- Full Flind Python regression: 265/265 PASS, and git diff --check PASS on macbook.
- Actual mobile Vitest, Markdown UI screenshot/link navigation, and Expo
  native builds remain unqualified because full JS deps are absent.

## Release

No public release, deployment, mobile app-store submission or OAuth
provisioning. Private repository; inherited Actions disabled. Source-wide
branding, SDK, backend and network egress gates remain open.
