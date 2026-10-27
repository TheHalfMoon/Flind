# Wave 165 — Django Python source coverage is complete in the local Git object store

## Background and purpose

The existing Wave 147 / Wave 164 Django sparse loader attempts tracked Python imports through a partial Git checkout with an extremely limited physical worktree. Earlier bounded `django.setup()` probes failed, and missing source was suspected, but a missing checked-out file and a missing Git blob are different things.

Added the read-only command:

```sh
python -m tools.flind.qualify_django_source_coverage_wave165 --root /path/to/Flind --ref HEAD --json
```

It enumerates tracked first-party Python files from `posthog`, `products`, `ee`, `common`, and `flind`, then distinguishes worktree copies, locally available Git object-only files, and Git blobs unavailable without fetching. Uses `GIT_NO_LAZY_FETCH=1`, `GIT_TERMINAL_PROMPT=0`, bounded output/object counts, and one read-only Git `cat-file --batch-check` invocation. It does not expand worktrees, install software, contact a cloud backend or falsely qualify a Django registry.

## Observed execution (2026-10-27, Mac)

Run using the existing pinned Python3.14.7 runtime, against the **older detached Wave 140 source checkout** at `14b4630c3` (not claimed to represent the current main revision).

| First-party Python source count | Measured |
|---|---:|
| Tracked Python files in five roots | 24,781 |
| Present as regular worktree files | 2,832 |
| Not checked out, but Git blobs verified locally | 21,949 |
| Missing from both worktree and local Git objects | **0** |

All tracked Python blobs for these roots were present in the local Git object database. This rejects the previous assumption that these specific Python blobs need remote downloading. It does **not** establish that every runtime source, config, template, compiled component, or third-party dependency is present, or that Django registry/migrations/E2E can boot.

Six independently executed Python unit tests **6/6 PASS** on disposable Git fixtures; cover full checkout, local-object-backed sparse checkout, fake missing blobs (no false pass), offline Git flags, invalid ref, non-repository and real Git batch checks.

## Independent Django diagnostic finding

A separate bounded, no-socket Django attempt against the old Wave140 checkout used the updated Wave164 import loader with explicit local-only Git reads, an **85-second deadline** and up to 120 traced modules. It stopped with `source_failure_kind=source_import_deadline`, `traced_source_modules=16`, and last successfully traced source `products/skills/backend/apps.py`. That last path is context and **is not proof of a missing or broken module**. Direct `git show` was empirically taking multiple seconds per invocation in this checkout, making repeated per-module Git subprocess startups a likely bottleneck. This motivates a persistent local Git-object reader as the next bounded engineering step instead of full source expansion.

## Release gate

`source_coverage_qualified` is **only** first-party Python source object coverage in the named five roots. `django_registry_qualified=false`, `migrations_qualified=false`, `end_to_end_qualified=false`, and `release_qualified=false` remain mandatory. Real first-party Django registry and migrations, Postgres/Redis/Kafka/ClickHouse ingestion, tenant isolation, dashboard/browser/desktop E2E, live Flind OAuth/PKCE and final zero-legacy artifact audits remain under issues #82 and #5.

Private repository, inherited GitHub Actions disabled, no publishing, deployment, paid services or shared database mutation; mandatory attribution remains intact.
