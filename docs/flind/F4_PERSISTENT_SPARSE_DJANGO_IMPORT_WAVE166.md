# Flind Wave 166 — Persistent offline Git import and tracked namespace packages

## Main engineering result

The Wave147 / Wave164 Django sparse source loader spawned `git show` once for every missing worktree Python module. On the older, detached Flind Wave140 partial checkout, a single `git show` could take **5–10+ seconds**, and the former 85-second bounded Django attempt reached only **16 traced modules** before the source import deadline.

This change replaces those repeated Git subprocess startups in the **actual child registry probe** with a single bounded `git cat-file --batch` reader that persists across module imports. This reader:
- Operates against the exact requested Git ref with `GIT_NO_LAZY_FETCH=1`, `GIT_TERMINAL_PROMPT=0`, and no remote download.
- Accepts only validated first-party tracked `.py` paths, verifies Git blob headers/framing, refuses oversized sources, and closes all file descriptors/processes at probe teardown.
- Leaves the original fixture-facing per-file loader behavior intact for unit compatibility.
- Restores Python PEP420-style namespace package discovery only for tracked first-party descendants, including nested packages such as `posthog.models.file_system` and namespace roots such as `common`, even if directories do not physically exist in the sparse worktree.
- Records only sanitized, repository-relative missing resource paths on `FileNotFoundError`, never arbitrary absolute paths or secrets.
- Increases the **configurable upper admission bound** to 1,200 modules while retaining the prior conservative CLI default (100) and hard time cap (180 seconds). Real runs specify their own lower bounds.

## Actual tests on 2026-10-27

**16/16 Python unit tests PASS**, including prior nine Wave164 tests, persistent Git process reuse, namespace nested/root package recovery, fixture import from locally available Git blob, unsafe path/missing module denial, resource path sanitization, and bounded import-limit refusal. Tests executed on pinned Python **3.14.7** in existing isolated Mac environment, including `-W error::ResourceWarning`. No newly installed dependencies, paid services, deployed workers or non-Flind databases.

Read-only isolated Django registry attempts (all against **older detached Wave140 Git source, not full current `main`**):
1. Pre-change `git show` approach: **16 modules / 85 seconds**, `source_import_deadline`.
2. Persistent batch reader (limit 180): **180 modules / 26 seconds**, import cap reached.
3. Persistent batch, limit 650: **248 modules**, missing `posthog.models.file_system` (virtual namespace package).
4. After nested package recovery: **499 modules**, missing top-level `common` (virtual namespace root).
5. After nested + root recovery: **952 modules / ~29 seconds**, `FileNotFoundError` for `products/growth/backend/enrichment/scoring_formula.hog`; confirmed tracked blob not locally materialized.
6. For an isolated scratch-only experiment, fetched the exact old-commit `scoring_formula.hog` (5,244 bytes) from private GitHub and wrote it ONLY to the **detached disposable Wave140 worktree**. A following probe reached **1,130 modules**, and now specifically reported another absent resource: `products/alerts/backend/logic/destination_stock_inputs.json`.
7. Fetched the exact old-commit tracked JSON into the same isolated scratch checkout (38,296 bytes). The last bounded run reached **1,002 modules** and then **source_import_deadline at 150 seconds**; registry remained unqualified. No further heavy runs were attempted because Mac free space had decreased to ~3.7 GiB.

Import progress is **not** successful Django initialization: none of the runs completed `django.setup()`, app model registry, migration graph, auth/API, tenant isolation, real ingestion, browser or release tests. The two materialized resources are **not** changes or commits to the user's original checkout or the Flind product branch.

## Important distinction

The Wave165 Python source inventory found 24,781 Python blobs locally present, but that check did not cover all runtime non-Python assets. These probes proved **two required tracked non-Python resources** were absent from the sparse worktree; one `.hog` file's Git blob was also missing locally. Therefore final Django source readiness requires a comprehensive, reproducible first-party runtime resource materialization plan and an adequately provisioned *owned disposable* environment; the batch importer alone is insufficient.

## Release and next gates

Issue #82 remains open: qualify the complete Python source/resources, actual Django registry/migrations on isolated Postgres, Redis/Kafka/ClickHouse ingestion and tenant-filtered API→Dashboard E2E, source package builds, integration/browser/desktop E2E and recovery. Issue #5 remains open for final Flind identity/package artifact scan. Public OAuth remains gated until actual first-party issuer/PKCE qualification. No deployment, publishing, paid compute, shared database writes, or removal of legally mandated attribution. Repository remains private with inherited GitHub Actions disabled.
