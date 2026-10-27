# Flind Wave 169 — Verified offline runtime-asset staging

## Problem and boundary

Waves 166–167 demonstrated two runtime resources required by Django imports which were not checked out in a sparse source tree and whose Git blobs were unavailable locally in another partial checkout:

- `products/growth/backend/enrichment/scoring_formula.hog`
- `products/alerts/backend/logic/destination_stock_inputs.json`

The Wave 169 tool verifies **exact Git object identity** and stages selected assets **only** into a separately marked scratch folder. It can use an offline seed directory containing bytes obtained through a separately authorized source, but the seed's Git blob digest **must match** the path tracked by the specified repository/ref. It never fetches Git objects over the network, modifies the actual source checkout, silently accepts untracked files, or marks Django/DB/E2E/release as qualified.

## Usage

The user/operator is responsible for creating a separate disposable target folder, NOT inside the source repository, and marking it explicitly with the exact file contents shown:

```sh
mkdir -p /tmp/flind-runtime-scratch
printf 'FLIND_RUNTIME_ASSETS_SCRATCH_V1\n' > /tmp/flind-runtime-scratch/.flind-runtime-scratch-v1

# Read-only check: does not write assets.
python -m tools.flind.stage_django_runtime_assets_wave169 \
  --repo /path/to/Flind --ref <EXACT_COMMIT> \
  --scratch /tmp/flind-runtime-scratch --json

# If the tracked blobs are not locally available, provide a separate,
# explicitly obtained seed tree with the same relative paths. Every seed
# is checked against the exact tracked Git SHA-1 or SHA-256 blob hash.
python -m tools.flind.stage_django_runtime_assets_wave169 \
  --repo /path/to/Flind --ref <EXACT_COMMIT> \
  --seed /tmp/flind-verified-seed \
  --scratch /tmp/flind-runtime-scratch --materialize --json
```

This **does not** automatically bind the resulting folder to Django. A later isolated source+resource worktree setup must consume these staged bytes; do not write them back into a real working tree without a separate qualification step. Never stage actual secrets, customer data or large unknown assets. Default asset selection is only the two proven missing Flind resources. An explicit `--asset` may select other tracked first-party runtime-candidate paths.

## Safety model

The tool verifies every requested path against Git `ls-tree` at the exact ref (regular blobs only). A local-only `cat-file` read is verified against the Git blob digest. If absent, an operator-supplied offline seed at that exact relative path is accepted **only after** independent SHA-1/SHA-256 Git-blob hashing. A dry run verifies but never writes. `--materialize` writes files atomically to an existing, marker-protected scratch directory distinct from the repository, and refuses conflicting existing content.

It rejects relative traversal, absolute paths, suspicious Windows alternate data stream syntax, reserved Windows file names, symlinks/junctions, absent/conflicting blobs, duplicate inputs, excessive file count, individual blobs larger than 2 MiB, combined size greater than 8 MiB, and missing scratch markers. It refuses partial writes if any requested asset fails preflight. Environment sets `GIT_NO_LAZY_FETCH=1`, `GIT_TERMINAL_PROMPT=0` and `GIT_OPTIONAL_LOCKS=0`.

## Executed verification — 2026-10-27

The exact tool and ten focused real-Git fixture tests were run on the authorized Windows 11 device `Abdulaziz`:

- Native Windows Python 3.14.7 / Git 2.56: **10 tests run; 9 PASS and 1 skipped** (Windows user account lacks symlink creation privilege).
- **Native WSL2 Linux Python 3.14.4:** **10/10 PASS, zero skips**, including the link-escape attack; command ran with `-W error::ResourceWarning` and completed in approximately 1.4 seconds.
- Tests include digest-matched seed recovery under synthetic simulated local-Git-object failure, tampered seed rejection, no partial output, dry run, correct atomic files/idempotence, source tree unchanged, marker/overlap refusal, reserved/ADS path inputs, and symlink attack refusal.

These are **synthetic fixture tests of the actual staging tool**, not current Flind backend integration or real-data testing. At the time of the initial Wave169 tests, the WSL Git CLI lacked credentials, so no current-main source-backed staging was attempted. A subsequent Wave170 qualification used authorized **Windows-native Git Credential Manager** to access private current `main`, performed bounded explicit downloads of the two real tracked resources, and staged them with matching Git-object digests. See `docs/flind/F4_CURRENT_MAIN_ASSET_ATTESTATION_WAVE170.md`. This does not constitute Django boot, migrations, or complete source qualification. GitHub connector access is used solely to integrate this fully tested source into the private repository.

## Remaining gates

Issue #82 remains **OPEN**: a dedicated, sufficiently provisioned isolated current-main checkout with complete Python+runtime assets; real Django app registry; disposable Postgres migrations/rollback; Redis/Kafka/ClickHouse/SDK→tenant-authenticated API→Dashboard; full browser and desktop E2E, recovery and security. Issue #5 remains open for final Flind identity/package/artifact audit. OAuth public ingress must remain gated until actual owner-controlled OIDC/PKCE/JWKS qualification.

Repository stays **private**, inherited GitHub Actions disabled, no publishing, deployment, or paid model/compute services. Preserve mandatory third-party licenses/attribution.
