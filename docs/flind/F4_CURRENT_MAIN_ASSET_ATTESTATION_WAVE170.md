# Flind Wave 170 — Exact current-main runtime-resource provenance

## Why this matters

Previous Django app registry attempts were conducted against an older detached Wave140 source checkout on a storage-constrained Mac. Wave167 proved two required first-party non-Python runtime files were missing from a sparse developer tree. Wave169 provided digest-verified offline scratch staging but initially tested only synthetic Git fixtures.

Wave170 adds **immutable per-file provenance** to the Wave169 tool, then exercises it against an actual new, authenticated, minimal private Flind main checkout on Windows. It verifies SHA-1 Git-object identities and SHA-256 content digests without altering the original source checkout. The stage report now includes `source_commit`, `git_blob_oid`, `sha256`, `size_bytes`, `verified_from` and `total_verified_bytes` for each complete dry-run or materialization.

## Exact source and assets — 2026-10-27

- Repository: `TheHalfMoon/Flind`, private.
- Current main tested: `343c6bf7c29bac17051f09363c96f66daf6e2b5a` (Wave169 merge).
- Clone mode: GitHub `--filter=blob:none --depth=1 --single-branch --no-checkout --sparse`; authenticated via **Windows-native Git Credential Manager**, not a token copied into scripts. Initial object store approximately **2.7 MiB**; no full worktree was checked out.
- The initial **offline** staging attempt against the blobless checkout correctly refused with `local_blob_unavailable` and exit code 2.
- The operator then deliberately fetched **only two** exact tracked resources via authenticated `git show HEAD:<path>` and wrote them to a separate temporary seed directory. No generic checkout expansion.

| Exact tracked path | Git blob SHA-1 | SHA-256 content | Bytes |
|---|---|---|---:|
| `products/growth/backend/enrichment/scoring_formula.hog` | `41ce8e6efc76abff6942f8082d69aea9eb9cf8cb` | `279de244b602f38ab191b6c1d0608abf8287d1b6c100de380cdd30568109b24b` | 5,244 |
| `products/alerts/backend/logic/destination_stock_inputs.json` | `48a9f1f77758218c35d99d8bdc41f08dcb4a0515` | `cfe21fadc0dfc7342f4e08df9d4b16de709105bbd2d5157f05b570a04965f1f0` | 38,312 |

A second **fresh blobless private shallow clone** was used to demonstrate the true missing-local-object fallback: `--seed` provided the two source-backed bytes from the first checkout; both passed the offline Git-object checksum and SHA-256 checks. The Wave170 `--materialize` run to a **separately marked scratch folder** returned:

```json
{
  "source_commit": "343c6bf7c29bac17051f09363c96f66daf6e2b5a",
  "files_verified": 2,
  "files_written": 2,
  "total_verified_bytes": 43556,
  "resource_staging_qualified": true,
  "django_registry_qualified": false,
  "migrations_qualified": false,
  "release_qualified": false
}
```

Each per-file receipt reported `verified_from=verified_seed`. This is real **current-main first-party tracked resource data**, not fabricated fixtures or user/customer information. It is a prerequisite for starting Django in a separate environment, **not** proof Django can start or any product flow works.

## Test evidence

- Original staging tool tests updated to validate immutable `source_commit`, full Git blob OID, SHA-256, byte count, origin attribution and dry-run/idempotence.
- **10/10 PASS** with zero skips on WSL2 Linux Python 3.14.4; `-W error::ResourceWarning` enabled.
- Real current-main staging to scratch: **2/2 exact tracked files verified and written**, exit code 0.
- The blobless second clone + offline seed test also passed on real current-main data with digest receipts. No Docker or application migrations ran.

## Limits and next engineering gate

This validates only the two known Django runtime resources. It does **not** materialize all Python modules, templates, migrations, bundles, or settings, and cannot alone provide the complete live Django runtime. No current-main full Django app registry, PostgreSQL migrations/rollback, Kafka/Redis/ClickHouse ingestion, SDK→API→Dashboard tenant-isolation E2E, frontend/browser E2E, first-party OIDC/PKCE, or shipping artifact audit was qualified.

**#82 and #5 remain OPEN / Release NO-GO.** Keep private repository, inherited Actions disabled, no paid compute or models, no publishing/deployment or shared database mutations, and retain all legally required third-party attribution.
