# Wave 222 — Real current-main original PostgreSQL migration apply / rollback

## Verification scope (2026-10-28)

Executed **the first-party** `tools/flind/qualify_isolated_postgres_wave173.py` against private Flind main commit `8343e14e539ca43f2853988ba189c2562df49959` (after merged Wave 221). The actual PostgreSQL server applied and rolled back one **original**, dependency-free first-party migration (`ai_training.0001_initial`). This was not a mocked or fabricated schema.

## Isolation and source admission

A new PostgreSQL **17.9** cluster was initialized under `/private/tmp/flind-wave222-isolated-pg` with a distinct `PG_VERSION` and `.flind-isolated-pg-v1` marker. A private Unix socket at `/private/tmp/flind-wave222-isolated-socket` on port **65444** was used, with `listen_addresses=''` **disabling all TCP listeners**. The synthetic database was `flind_wave222_synthetic`.

Before the Django check, an actual SQL query confirmed the connected database name, `inet_server_addr() IS NULL` (true), and the exact private server data directory. The original qualifier independently rechecked its source scratch marker, source commit, migration graph, socket, database name, read-only session, real server data directory, and one-migration allowlist. It denies unrelated Python network sockets. Mac's shared system PostgreSQL and PgBouncer, the Windows Zyara service, and every other project's database were untouched.

The 3,706 canonical first-party Git-tracked migration Python files in the marked scratch source were previously attested. The original project Python3.14.7 runtime used only locally pinned dependencies and the tracked `packages/personhog-proto` workspace. One historical noncanonical migration path was preserved without renaming or deletion.

## Exact first-party result

The run used:

```sh
python tools/flind/qualify_isolated_postgres_wave173.py \
  --root /private/tmp/flind-wave218-source --ref HEAD \
  --pg-data /private/tmp/flind-wave222-isolated-pg \
  --pg-socket /private/tmp/flind-wave222-isolated-socket \
  --pg-port 65444 --dbname flind_wave222_synthetic \
  --apply-rollback --json
```

Original process **exit 0**, with these verified receipt fields:

| Check | Result |
| --- | --- |
| Exact source commit | `8343e14e539ca43f2853988ba189c2562df49959` |
| Django registry | **PASS**, 115 apps |
| Canonical migration files staged | **3,706** |
| Migration graph | **PASS**, 839 nodes, 3,335 disk migrations |
| Empty-database plan | **PASS**, 839 planned, 92 leaf targets |
| Read-only connection to dedicated PostgreSQL data directory | **PASS** |
| Original `ai_training.0001_initial` apply | **PASS** |
| Original `ai_training.0001_initial` rollback | **PASS** |
| Remaining app migration records after rollback | **0** |
| Remaining user tables after rollback | **0** |
| All original migrations applied and reversed | **NOT QUALIFIED** |
| Original Kafka → Rust → Node → ClickHouse E2E | **NOT QUALIFIED** |
| Release | **NO-GO** |

The original qualifier inspects the exact sole `CreateModel` operation and refuses dependency changes or a multi-migration plan. That one original migration is not evidence that the other migrations were applied.

The test wrapper stopped only the Wave222 private PostgreSQL instance in an EXIT trap. After the run, an independent PostgreSQL 17.9 `pg_ctl -D /private/tmp/flind-wave222-isolated-pg status` confirmed **no server running**, exit code 3, and the private socket directory was empty. The data directory was retained strictly as synthetic local evidence.

Original first-party safety regression suites `test_qualify_isolated_postgres_wave173` and `test_ephemeral_postgres_wave54`: **11/11 PASS**. They cover marker/path/port refusal, operation selection, binary guardrails, lifecycle stop and isolated SQL behavior.

## Remaining release blockers

The isolated service test from Wave216 **failed 4/4** due to missing genuine PostgreSQL and ClickHouse migrations; this current-main one-migration result does not qualify the full databases. Continue with ownership-verified disposable **full original** PostgreSQL + ClickHouse migration apply/idempotence/rollback, then real Kafka → Rust → Node → durable ClickHouse tests, authentication, cross-tenant isolation, SDK/browser and distribution identity. Windows C storage exhaustion and WSL I/O errors remain a separate blocker under issue #253.

Keep Flind **PRIVATE**; GitHub Actions disabled, **no publication, deployment, paid services, or modifications to other projects' data**. Preserve mandatory third-party legal notices.
