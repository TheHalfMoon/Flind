# Atomic embedded Node API tool materialization

Status: source guard and native Rust tests require exact-head verification.

## Security risk

Flind's staged Rust CLI materializes a separately built Node API tool bundle
before delegating API operations. Previously `fs::write` opened a
predictable versioned file, following a malicious preexisting symlink.
On an incorrectly permissioned local CLI home, this could truncate
an unrelated file **before Node starts**, including when the injected
API bundle was otherwise correctly selected.

## Fix

Only the compile-embedded bundle is available to optimized CLI builds
(see merged PR #91). The materializer now:

1. Creates the version directory, then refuses symlinks at the managed
   `api-cli` directory and its version child.
2. Creates an unpredictable same-directory temporary file using the
   already-pinned `tempfile` dependency.
3. Writes all embedded bundle bytes and syncs them to disk.
4. Persists the temporary file by renaming the directory entry to the
   versioned filename. This **replaces**, rather than dereferences,
   an existing final-path symlink.
5. Canonicalizes and validates the resulting regular file before
   handing it to the Node subprocess. Any materialization error
   returns a fail-closed `MaterializeFailed`.

Native Rust regression tests construct a synthetic symlink victim
file, an adversarial symlinked version directory, an adversarial
symlinked API directory, and a stale executable with known bytes.
They prove no victim-file modification and no leftover staging file.
Additional dependency-free source contracts check ordering and block
reintroducing direct final-path `fs::write`.

## Remaining risks and release gate

This is **not** a complete process-privilege isolation, TOCTOU, or
remote-code audit. An attacker with write access to the CLI home can
still race the directory or replace a file after validation. Windows
directory junction/reparse-point behavior also requires independent
Windows filesystem tests. Dedicated, user-owned private install
directories and an egress-qualified Node bundle remain necessary.

This patch is not a release authorization. No public CLI binary,
installer, package, tag, deployment or SDK publication until the
owner explicitly says `GREEN LIGHT FLIND`. Preserve upstream
copyright, licenses, and provenance obligations.
