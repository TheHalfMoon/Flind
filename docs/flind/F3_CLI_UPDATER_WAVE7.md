# F3 Wave 7 — Fail-closed Flind CLI self-update

## Discovered security risk

The copied Rust CLI updater referenced a source-provider release host for
manifest discovery, downloaded shell installer code, and executed that code.
On systems with an install receipt, a Flind-branded CLI could therefore
install a different product, overwrite binaries or run third-party shell
content without an independently qualified Flind release channel.

## Change

- Remove all hard-coded external release-manifest/install-script URLs.
- Remove the remote manifest fetch, installer download and shell execution
  path from the CLI update command.
- The update command now returns an explicit error before contacting any
  network or replacing a binary. It does not claim that a Flind release
  channel, Homebrew formula, Cargo binary or npm registry publication exists.
- Historical install-path classification logic and tests remain for future
  migration compatibility, but they do not authorize self-updates.
- No remote release URL or operator-controlled host is invented.

## Evidence / gate

- Rust source formatting and source-focused standard library Python
  regressions in tools/flind/test_cli_updater_isolation.py.
- A Rust unit regression exercises update() and checks the error.
- Build and test the actual CLI crate using an appropriately populated Cargo
  cache; validate the CLI's update command on Windows, macOS and Linux
  before claiming runtime qualification.
- Release tooling must later be rebuilt around actual Flind-controlled,
  cryptographically verified artifacts and secure download checks, not
  curl-to-shell of an untrusted historical installer.

This is intentionally a temporary disabled feature rather than an unsafe
working updater. Other inherited Rust CLI telemetry, embedded API bundle
and login hosts are separate blockers. **No public release.**

## Current local evidence

- 164 dependency-free Flind Python tests **PASS** on the full checkout.
- Rust source formatting via rustfmt --check **PASS**; source has no inherited
  download URL, reqwest fetch or shell-spawn execution path in update.rs.
- The new Rust unit test for update() was added but **not run**: offline Cargo
  resolution reports missing public crate `inquire` in the local cache. Full
  Rust CLI compilation and E2E updater behavior remain blocked, not qualified.
- Repo-wide literal destination audit also remains red: 2,707 candidate
  inherited outbound references in 1,615 runtime source files. This is a
  static inventory, not actual network egress evidence.
