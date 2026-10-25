# Wave 96 — Refuse Django migration startup failures before database allocation

## Problem

The original sustained migration runner protected against incorrect Python dependencies and insufficient free disk, but it went straight to creating a disposable PostgreSQL cluster. A sparse repository checkout can have the exact 201/201 locked runtime dependencies while omitting required first-party Python modules (e.g., `flind` or `ee`). This caused an avoidable `ModuleNotFoundError` **after** temporary PostgreSQL had started, without any migration row applied.

This is separate from the full-schema migration duration/performance blocker.

## Change

`tools/flind/qualify_sustained_migrations_wave75.py` now runs a bounded, read-only `manage.py help migrate` import preflight in the existing sanitized, unreachable-service Django environment **before** allocating a disposable database. It:

- First retains the 10 GiB temporary-disk reserve and 201-direct-dependency lock admission.
- Runs the actual Django management-command import with 60-second timeout, no inherited credentials, no production database connection and no deployment warnings gate.
- Returns a fixed, sanitized exception *class* if it cannot import the command; does not expose raw traceback, host paths, user names or tokens.
- Refuses to invoke `isolated_postgres` on import failure; preserves the migration/PG code and original completion conditions after success.
- Adds an explicit `django_migration_preflight_passed` receipt separate from `full_schema_migrations_completed` and hard-coded `release_qualified=false`.

## Evidence — October 25, 2026

- **44/44** targeted unit regressions for migration orchestration and diagnostics PASS, including **7 new Wave 96 tests**.
- A sparse current-main checkout with pinned Python **3.14.7** and fully locked dependencies was tested with the real preflight. It returned exit 2, `django_migration_preflight_passed=false`, `ModuleNotFoundError`, **before** allocating PostgreSQL.
- The fuller Wave 84 source checkout (with `flind` and `ee` restored to its sparse include set) passed the same real preflight: `passed=true`.
- Both checks used the actual local Python 3.14.7 runtime and no external services. No shared PostgreSQL database was modified.
- Other runtime execution, schema migration completion and release gates remain separate.

## Release boundary

An import preflight is not proof of complete schema application. Full schema, production SDK→Kafka→ClickHouse→API→UI readback, OAuth, tenant isolation, frontend production build and browser E2E remain open under Issue #82. Keep Flind private and inherited Actions disabled; no publication, deployment, paid services or removal of mandatory legal source attribution.
