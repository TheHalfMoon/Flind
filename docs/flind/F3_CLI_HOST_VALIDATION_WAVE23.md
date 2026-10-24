# F3 Wave 23 — CLI saved credentials and login host boundary

## Threat model

Central CLI host validation formerly required only that a host parse as some
URL; a stale saved credential for the inherited vendor's cloud could therefore
still be used by CLI commands. The OAuth device flow sends requests before the
normal InvocationContext host validation, and both device-code/poll clients
followed HTTP redirects.

## Mitigations

- Validate central CLI API hosts as absolute, hostname-bearing HTTPS origins.
- Allow loopback HTTP for local development, but refuse remote plaintext HTTP.
  Operators hosting on LAN IP addresses must use HTTPS or a local loopback
  proxy; this is a deliberate compatibility constraint for bearer-token
  protection.
- Normalize trailing DNS root dots before rejecting inherited provider cloud apex/subdomains, embedded URL credentials,
  extra paths, query parameters and fragments.
- Apply the same approved-host condition to OAuth device-code login before
  sending any request.
- Disable automatic HTTP redirects on device-code and polling clients.
- Keep existing environment variable names and saved credential structure for
  compatibility, but reject unsafe destination values instead of silently
  migrating them.

## Validation

- Rust unit tests cover allowed and rejected URLs and the explicit OAuth
  upstream-host refusal.
- Python regression guards verify that credential URL validation occurs
  before client construction and that device-flow clients cannot auto-follow
  redirects.
- Rust formatting / offline Cargo and the full Flind Python regression suite
  are required prior to merge.

## Release restrictions

This change is not a full CLI or SDK live egress qualification. A local test
does not prove redirect behavior against real malicious servers, DNS-rebinding
resilience, or that every other CLI tool has audited egress behavior.
No data migration, cloud service enablement or public release is authorized.

## Verified on macbook, 2026-10-24

- Rust CLI library suite: **260/260 PASS** (`cargo test --offline --locked
  --manifest-path cli/Cargo.toml --lib`).
- Flind Python suite: **239/239 PASS** (`python3 -m unittest discover -s
  tools/flind -p 'test_*.py' -q`).
- Rust formatting and whitespace check: PASS.
- Added trailing-DNS-root-dot normalization after review; it rejects
  `posthog.com.` and its subdomains with trailing dots as the same inherited
  provider. The existing login source scanner remains green because the
  blocked-host test constructs the upstream fixture, rather than defining an
  inherited network default.
- Real OAuth handshake, login server, DNS rebinding and network captures:
  **not qualified**. No public release.
