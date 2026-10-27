# Wave 171 — Current-main Django app registry finally qualified

## Actual first-party runtime result (2026-10-27)

**PASS**: `django.setup()` and `django.apps.apps.get_app_configs()` completed in a child Python process using real tracked code from the **private Flind `main` commit `1905e9afb0f25f2685f042485b59f4c433403ffe`**.

Observed final JSON report from the exact Wave171 proposed script:
```json
{
  "phase": "sparse-git-django-app-registry",
  "source_ref": "HEAD",
  "source_commit": "1905e9afb0f25f2685f042485b59f4c433403ffe",
  "django_registry_qualified": true,
  "app_count": 116,
  "traced_source_modules": 1564,
  "migrations_qualified": false,
  "app_http_qualified": false,
  "real_ingest_qualified": false,
  "tenant_isolation_qualified": false,
  "release_qualified": false
}
```

The original Wave147–166 isolated registry test's prior **1,200 module ceiling** was too small; a preliminary *current-main* run exited with `source_import_limit` at 1,100 configured modules. An explicitly bounded scratch test with a 5,000 ceiling reached 1,564 and returned 116 registered apps. Wave171 therefore raises the tool's **absolute admission cap to 3,000** and sets a practical default of 2,200 while preserving the 180-second absolute process deadline. This does not remove bounded resource controls.

Wave171 also records the **resolved, immutable, local Git source commit** (instead of treating `HEAD` as sufficient provenance), and refuses a source ref that cannot be resolved. Everything is read-only at the source-tree layer.

## Isolated environment

- macOS with preexisting pinned, free Python **3.14.7**, Django **5.2.18** and previously installed project Python dependencies; no new paid resources or large downloads.
- Fresh, disposable **`/private/tmp/flind-wave171-current-boot`** clone from the actual private Flind `main`, made with `--filter=blob:none --depth=1 --single-branch --no-checkout --sparse`. Initially approximately 2.8 MiB `.git` object store, plus physically materialized first-party `pyproject.toml`.
- Read-only Git alternates to the already-existing *authorized local Flind Git object store*, allowing local-only original Python module reads without cloning 62k tracked files. `GIT_NO_LAZY_FETCH=1` and `GIT_TERMINAL_PROMPT=0` prohibit implicit Git object downloading during the probe. The probed Git **ref is the new main clone's HEAD**, not the older local checkout's HEAD. First-party imports are resolved by the persistent local Git blob loader at the new ref.
- Both known runtime resources `scoring_formula.hog` and `destination_stock_inputs.json` were copied **only** into this disposable new clone after checking their Git object hashes against the exact current-main commit (5,244 and 38,312 bytes).
- The child process denies Python socket connections, uses synthetic nonfunctional database/Redis/Kafka/ClickHouse URLs, disables `__pycache__`, and enforces both a source-import budget and wall deadline. No DB migrations, real API calls or external network sessions.
- Original Python tool unit suite against the exact Wave171 proposed branch source: **17/17 PASS** under `-W error::ResourceWarning`, exit 0. The production-like Django registry probe against current Flind main: **116 apps, 1,564 traced modules, exit 0**, observed run approximately 30 seconds.

## What this result proves and does not prove

Proves actual installed Django + imported, real first-party current-main Flind Python app definitions successfully register with Django under *synthetic offline runtime settings*. This is a material advance beyond the earlier Wave140 attempts, which timed out or hit missing non-Python resources.

**Does not prove** full deployment, a non-sparse source build, correct DB migrations/history or rollback, real service sockets, valid tenant-authenticated API routes, Redis/Kafka/ClickHouse ingest, browser/desktop/mobile E2E, OAuth login, final branding, or release readiness. In particular, Git-only modules may have different migration discovery behavior from physical on-disk modules; **do not claim migration qualification based on the Django registry result**.

Next: read-only, current-main migration filename + dependency inventory; then isolated disposable PostgreSQL/Redis/Kafka/ClickHouse integration, safe migration graph/rollback, SDK→tenant-filtered query dashboard and E2E. Issue #82 and #5 remain open with release **NO-GO**. Private repo, inherited GitHub Actions disabled, no paid compute/model, no deployment/publication, preserve legally required third-party attribution.
