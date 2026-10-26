# Wave 147 — Bounded Django registry admission from sparse, tracked Git source

## Problem addressed

Flind's 451-package exact Python3.14.7 environment is installed and **201/201 directly pinned packages match `uv.lock`**, but a full Django app-registry check cannot finish in the partial/sparse Git checkout on the shared 8 GiB Mac: the source workspace excludes first-party app modules, and broad sparse expansion can attempt to materialize **thousands of temporal files**, exceed Git lazy-fetch limits, or remove previously hand-materialized files. Repeated one-off manual source copies are not a reliable qualification method.

## New reproducible tool

`tools/flind/qualify_sparse_django_registry_wave147.py`:

- Enumerates **tracked first-party Python source names once** from a selected Git commit (allowlisted `posthog`, `products`, `ee`, `common`, `flind` roots).
- Uses a bounded importlib fallback to load a **missing, tracked `.py` or `__init__.py` blob** from `git show` *in memory*. Existing source files and normal installed dependency imports have precedence. Never broadens the sparse worktree or generates a source file.
- Rejects unsafe module identifiers, arbitrary paths, Git refs prefixed with `-`, source blobs over 2 MiB, and attempts beyond the configured import count/time limit. Every blob read has an 18-second timeout, source enumeration 45 seconds.
- Runs Django in a **child process** with a synthetic `SECRET_KEY`, dummy loopback DB/Kafka/ClickHouse/Redis URLs, the exact pinned Python interpreter, and Python socket connections disabled. Parent enforces a deadline and kills the process group on timeout. No migrations, ingestion, HTTP requests or database writes are attempted.
- Reports only bounded structured success/failure and the number of tracked modules loaded. `release_qualified=false` is unconditional. The Git subprocess may need network to fetch missing Git objects if the repository is a partial clone; this network activity is *only source retrieval*, not application egress.

## Executed tests (2026-10-26)

Fetched the exact PR-branch source into the detached disposable Mac worktree without changing the original user's Flind checkout.

`PYTHONPATH=. python -m unittest -v tools.flind.test_sparse_django_registry_wave147`: **6/6 PASS** (0.55 s). This covers a real temporary Git repository, package load without writing to the working tree, exact tracked files, unsafe module rejection, import budget, deadline argument validation, and no false app/release claim.

Actual `python qualify_sparse_django_registry_wave147.py --root /tmp/flind-wave140-source --ref HEAD --timeout 85 --max-imports 55 --json`: **BLOCKED after 12 dynamically loaded first-party Python source modules**. A further Git partial-clone `git show` lazy fetch exceeded the per-blob timeout, so the tool stopped with a sanitized `ImportError`, not a green registry receipt. It did **not** qualify `django.setup()`; no independent Django DB/HTTP test was run. The source worktree remained unchanged/clean, free disk ~14 GiB and memory recovered after the bounded subprocess terminated.

## Next release gates

Move a complete, bounded source checkout to suitable no-cost storage/compute or prefetch only needed tracked Git objects into a cache, then re-run `django.setup()` and schema inspection against a dedicated isolated PostgreSQL cluster. Full DB migration, authentication, production Node/Rust/Kafka/ClickHouse capture and tenant-filtered API/Dashboard/browser E2E are still required in issue #82. Full first-party identity—including OAuth endpoints and remaining SDK/protocol identifiers—remains issue #5.

This is a qualification/testing tool, not a production Django source loader or application runtime requirement. The repository stays private, inherited Actions disabled, no publishing/deployment/paid resources, and legal notices preserved.
