# CLI nested host overrides and inherited Node hooks

Status (2026-11-13): **16/16 Rust API proxy unit tests and 5/5 actual CLI
subprocess tests passed on Windows-hosted WSL Ubuntu**, using pinned
offline Cargo dependencies; **13/13 Python source contract tests passed**
and Rustfmt is clean. Exact-head GitHub CI still required before merge.
This is a follow-up to Flind's merged API proxy host validation (PR #84).

## Threat model and protection

The parent Rust `posthog-cli api` had already validated the top-level
`--host`, `POSTHOG_HOST`, `POSTHOG_CLI_HOST` and the saved CLI host,
and passed one normalized server origin to the delegated Node process.

The command also forwarded every unparsed nested argument to Node,
however. A delegated Node CLI may prioritize nested options such as
`--host=https://us.posthog.com`, `--api-host`, `--base-url` or
`--config` over the validated parent origin. The safety requirement
is that **no nested transport/config override reaches Node with a
personal API key**. Choose the instance origin with the top-level
Flind CLI `--host`, before `api`, or with one approved environment
host. The nested-argument preflight rejects both `--key value` and
`--key=value` forms, case-insensitively, before resolving the script
or spawning a Node subprocess.

A separate inherited environment hazard is `NODE_OPTIONS`: Node
may preload a JS hook before the bundled API CLI even starts. A hook
could read all injected API keys and bypass any host restrictions.
The child therefore has `NODE_OPTIONS` and `NODE_PATH` explicitly
removed, in addition to inherited vendor analytics settings.

## Regression checks

Rust unit tests cover forbidden nested host/config override flags,
ordinary agent-friendly `tools`, `search`, `info`, `call --json`
and JSON body strings that contain host properties. Process tests
invoke the actual CLI binary against a synthetic marker-writing
Node script. With a nested inherited-provider host the child script
must **never execute**. The original positive Node argument-forwarding
test intentionally injects `NODE_OPTIONS=--require=...`; the
preload sentinel must **not** execute, while ordinary CLI argument
forwarding continues.

Dependency-free Python and Rustfmt CI source guards complement
local WSL `cargo test --locked --offline` verification. These are
not substitutes for a network-namespace audit of the separately built
Node bundle, the vendor-to-Flind CLI executable rename, original
installer/update removal, or production auth auditing.

No public packages, binaries, tags, hosted deployment or installer
without the owner's explicit `GREEN LIGHT FLIND`. Retain source
license and copyright obligations for donor components.
