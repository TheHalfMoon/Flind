# Wave 167 — Read-only offline Django runtime resource audit

## Why

Wave166's sparse Django probe progressed through roughly 1,000 tracked Python imports, then needed two non-Python startup files: `products/growth/backend/enrichment/scoring_formula.hog` and `products/alerts/backend/logic/destination_stock_inputs.json`. A complete **Python Git object inventory** from Wave165 is insufficient to prove these data resources exist locally.

Added `tools/flind/qualify_django_runtime_assets_wave167.py` and 7 regression tests. This report is a source/resource prerequisite only, **not** actual Django startup or final product qualification.

## Reproduce

```sh
python -m tools.flind.qualify_django_runtime_assets_wave167 --root /path/to/Flind --scope traced --ref HEAD --json
```

Default `--scope traced` inspects only the **two startup resources proven necessary by Wave166**, without modifying or downloading them. `--scope all` is an explicitly separate, bounded inventory for common first-party candidate extensions (`.hog`, `.json`, `.yaml`, `.yml`, `.toml`, `.sql`, `.graphql`, `.proto`, `.csv`). Asset inventory is NOT a complete runtime dependency graph. No wildcard remote downloads, global installation, Git checkout expansion, database writes, or runtime secrets.

The scanner uses Git `ls-tree` and offline `cat-file --batch-check` with `GIT_NO_LAZY_FETCH=1`, disables terminal prompts/optional locks, and avoids querying blobs already materialized in the worktree. It distinguishes `worktree`, `git_blob_only`, `unavailable`, and `not_tracked_at_ref`. All reports set Django registry, migrations, E2E and release qualification **false**. Broad inventory times out and fails closed instead of claiming success.

## Actual Mac execution — 2026-10-27

Real 8GiB Mac, no paid services, pinned Python 3.14.7 / Django 5.2.18:

- **7/7 unit tests PASS**, including genuine disposable Git fixture, both required traced resources present, sparse-but-local-blob-only case, absent blob, missing tracked dependency, invalid Git ref and non-repository refusal. `-W error::ResourceWarning` PASS.
- The optional broad scan over nine candidate extensions on the older detached source checkout timed out when reading the Git object store (even after increasing the bounded subprocess timeout). It is **UNQUALIFIED**; no broad counts are claimed.
- **Detached Wave140 scratch checkout** (Git HEAD `14b4630c3`): both traced startup resources are physically present because Wave166 copied them from the exact historical Git revision into that **scratch worktree only**. `tracked_candidates=2`, `present_in_worktree=2`, `asset_coverage_qualified=true` **for those two traced files only**. Django registry remains false.
- **Separate preexisting sparse Flind developer checkout** (older local branch, NOT current private GitHub main): both exact traced paths are tracked but **neither is present in the checkout nor locally available as a Git blob**. `tracked_candidates=2`, `unavailable_without_fetch=2`, `asset_coverage_qualified=false`, Django registry/release false. This was read-only: no files were written to that developer checkout.
- Free Mac storage remained approximately 5.6 GiB after audit.

This demonstrates a concrete materialization difference between partial checkouts and makes the missing-resource gate reproducible without starting a heavy service stack. The resource files were not committed, rewritten, or embedded in Flind. The full-product runtime and source distribution must eventually be qualified at the **current main commit** in a disposable sufficiently provisioned environment.

## Release and ownership boundaries

Issues #82 (Django/DB/Kafka/ClickHouse/SDK→tenant-authenticated API→Dashboard/browser E2E) and #5 (full Flind identity and release artifact audit) remain **OPEN / NO-GO**. Public OAuth remains gated until real issuer/JWKS/PKCE integration. Repository stays private with inherited GitHub Actions disabled. No deploy/publish/paid resources or shared database modifications. Preserve third-party legal notices.
