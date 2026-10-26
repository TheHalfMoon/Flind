# Wave 139 — Require exact Django direct-dependency lock for F4 readiness

## Previously misleading gate

`tools/flind/qualify_backend_runtime.py` checked whether the active Python patch matched `pyproject.toml`, whether `django` could be imported, and whether PostgreSQL/Redis/ClickHouse were reachable. It did **not** check Flind's exact pinned application dependency graph. A minimal Django import could therefore report `prerequisites_ready=true` despite many application imports being absent.

## Implemented

Added an independently required `django_lock` check to the read-only backend readiness report. It uses the project's existing `qualify_django_lock.audit_runtime_lock()`, which compares applicable **direct** dependencies from `pyproject.toml` with installed distributions and exact versions from the checked-in `uv.lock`. If any direct package is missing, mismatched, unlocked, or has an unverified marker, the backend prerequisite gate refuses. It emits **aggregate counts only**, not environment paths or dependency diagnostics. Missing/invalid lock evidence fails closed. It does not contact services or install anything.

The returned `release_qualified` remains **false regardless of the prerequisite result**; a matching direct lock is necessary but still not proof of Flind migrations, runtime/API, data durability or tenant-isolated E2E.

## Real offline-and-free environment evidence on Mac

Used *isolated*, temporary tools with no system-default modification:
- The global user `uv 0.11.20` (June 2026) could not discover Python 3.14.7 from its frozen distribution catalog. `uv 0.13.5` was downloaded as an isolated wheel into `/tmp` and correctly discovered the compatible official `python-build-standalone` Python 3.14.7 distribution.
- Installed the exact Python `3.14.7` into `/tmp/flind-wave139-python3147-updated-uv`, and created a virtual environment with locked Django `5.2.18` (plus its two wheel dependencies), without changing the Mac's default Python.
- The exact Flind Python check returned **PASS** and Django import returned **PASS**, but the actual direct dependency audit still found **201 applicable dependencies, 1 exactly installed, 198 missing, 2 wrong versions**.

## Branch-source tests actually executed

Fetched the proposed GitHub branch into an isolated temporary package copy, symlinking only the existing tracked `pyproject.toml` and `uv.lock`, and ran the original `test_backend_runtime_readiness_wave48` suite updated with four new lock tests under Python3.14.7/Django5.2.18.

**21/21 PASS, exit 0**, including full-vs-partial lock, aggregate safe errors, no accidental release promotion, and exact Python patch checks.

Ran the actual updated `qualify()` in that environment: Python and Django READY; `django_lock` BLOCKED with exact aggregate counts. Redis/ClickHouse default-port health checks remain blocked (their separately verified process-owned native test engines were not left running). This is expected; Wave138 already proved the compatible three native services together on temporary loopback ports.

## Outstanding work

**No full Django installation or production app bootstrap.** The project still has hundreds of dependencies and 198 missing direct packages in the tested minimal environment; installing the entire workspace on the shared 8 GiB / ~16 GiB-free Mac is not currently qualified as resource-safe. Next: a resource-safe, disposable no-cost build environment and full exact locked install, isolated Flind migration graph and runtime, actual SDK→capture→ingest→ClickHouse→authenticated API/Dashboard proof, tenant isolation and failure recovery. Issue #82 stays OPEN, release **NO-GO**, repository private, no deploy/publication/paid resources. Mandatory legal attribution retained.
