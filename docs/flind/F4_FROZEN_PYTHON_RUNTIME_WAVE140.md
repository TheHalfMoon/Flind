# Wave 140 — First successful exact frozen Python production-dependency install

## Actual Mac qualification (2026-10-26)

A separate detached, sparse Git worktree based on private Flind `main` was created in `/tmp/flind-wave140-source`. The original working checkout and existing Python/uv installations were left unchanged. The detached checkout included the three required local Python workspace members (`tools/hogli`, `packages/owners-yaml`, `packages/personhog-proto`). Without them `uv sync` fails before installation because its local workspace source is missing.

The Mac's globally installed `uv 0.11.20` could not discover the pinned Python patch and is older than `pyproject.toml`'s required `uv>=0.13.4`. A copy of **uv 0.13.5** was installed into an isolated `/tmp` directory from the free public wheel index. Using it, the exact pinned **Python 3.14.7** was installed in a separate temporary directory without changing the system default.

The frozen production/default-only dependency install was then run with no dev/default groups and without installing the Flind root package itself:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/flind-wave140-runtime-candidate \
UV_CACHE_DIR=/tmp/flind-wave140-uv-cache \
UV_CONCURRENT_DOWNLOADS=2 UV_CONCURRENT_BUILDS=1 UV_CONCURRENT_INSTALLS=2 \
/tmp/flind-wave139-uv-isolated/bin/uv sync \
  --frozen --no-dev --no-default-groups --no-install-project \
  --python /tmp/flind-wave139-python3147-updated-uv/cpython-3.14.7-macos-aarch64-none/bin/python3.14 \
  --no-progress
```

Use the same commands with appropriately owned scratch paths in a future environment. This is a record of an actual command, **not** a proposal for a globally installed runtime. A `--no-build` first dry-run correctly refused because `bingads==13.0.26` lacked a binary wheel. A source-build-aware dry-run of the complete workspace succeeded and projected **451** packages. A bounded real install (180-second deadline, 13 GiB free disk reserve, low download/build parallelism) succeeded with **exit 0**, prepared and installed 451 pinned packages in around 58 seconds. The build included `bingads`, `zstd`, `thrift`, and workspace distributions. No application deployment or paid service occurred.

The real installed interpreter then passed the existing `audit_runtime_lock()`:

- Python **3.14.7**, exact project patch: PASS
- Django **5.2.18**, exact `uv.lock` version: PASS
- 202 declared direct requirements, 201 applicable to macOS arm64
- **201/201 applicable direct dependencies at pinned versions**
- **0 missing / 0 mismatched / 0 unlocked / 0 unverified markers**

A source-backed standalone receipt is now available:

```bash
PYTHONPATH=. /tmp/flind-wave140-runtime-candidate/bin/python \
  -m tools.flind.qualify_frozen_python_runtime_wave140 --json
```

The first-party `test_frozen_python_runtime_wave140` suite ran **5/5 PASS** under that exact environment against files fetched directly from the GitHub branch. It tests matching runtime, deliberate mismatch refusal, corrupt lock refusal with sanitized messages, invalid negative counts, and no accidental release promotion.

## What the successful install does NOT establish

This is a **Python distribution/runtime-only milestone**, not successful Django app boot or a release gate. The private detached Git worktree is a sparse checkout and does not contain all first-party Django apps. A network-denied `django.setup()` smoke progressed through settings once the needed modules were included, but stopped on missing first-party source paths (eventually `products.warehouse_sources`). A full worktree expansion hit Git partial-clone open-file/fetch limits; targeted expansion was halted rather than cause heavy resource pressure. This is insufficient source coverage, **not** a proven runtime defect or a passing app registry test.

All real test sockets were denied at the Python level; dummy loopback database URLs were used and no migrations or user data writes occurred in this installation wave. Existing native PostgreSQL/Redis/ClickHouse qualification was already recorded in Wave138.

`full_source_checkout_available=false`, `django_app_registry_qualified=false`, `django_migrations_qualified=false`, `real_ingestion_and_dashboard_qualified=false`, `tenant_isolation_qualified=false`, `release_qualified=false`. Keep issue #82 open. Next step is a safely complete source checkout, actual Django setup/migrations against a disposable Flind stack, Node/Rust workers, capture→Kafka→ClickHouse→authenticated query→Dashboard end-to-end and authorization/recovery tests.

No publishing, deploy, paid cloud, GitHub Actions enablement, global Python mutation, shared database access, or deletion of legal attribution was performed. Repository remains private.
