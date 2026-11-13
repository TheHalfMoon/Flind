# Flind migration data-preservation canary (two stores)

Status: the original positive-preservation run passed GitHub CI in merged PR #72.
The added live negative controls require their own exact-head GitHub CI.
This is a synthetic test for idempotence with *existing test data*.
It is not qualification of an upgrade between released product versions.

## Motivation

The existing migration workflow runs against fresh databases and repeats
migrations to check idempotency. But without preexisting rows between runs,
a destructive or incorrectly replayed migration might still pass.

## Test sequence

In the same GitHub Ubuntu ephemeral runner already used for migrations:

1. Start the real PostgreSQL 15, ClickHouse, Kafka, Zookeeper and Redis
   test stack, apply Django/persons/ClickHouse migrations from scratch.
2. Fail closed unless the GitHub runner uses the known throwaway local
   Postgres URL, expected ClickHouse database/host, `DEBUG=1`, exact
   evidence path and explicit synthetic flag.
3. Refuse a preexisting synthetic marker table in either store.
4. Create disposable marker tables with **two synthetic tenants** (101 and
   202) and distinct fixed marker/count values in PostgreSQL and ClickHouse.
   Capture ordered baseline rows to ephemeral CI evidence files.
5. Run the existing three-store migration command a second time.
6. Fetch the same tenant records from both stores and require exact
   row-by-row equality, with no deleted/duplicated/mutated marker. Fail the
   workflow if either datastore differs.
7. Demonstrate that the **same** PostgreSQL row comparator rejects a real
   mutation of tenant 202 inside the disposable test table, then restore the
   original marker and require parity again. Independently demonstrate that
   the ClickHouse comparator detects loss of tenant 202 from its disposable
   test table, reinsert it and require parity again. These mutations affect
   no customer or product domain tables.
8. Drop the two owned marker tables only after all comparisons pass; the
   final ephemeral runner teardown removes remaining test containers.
   Report only digests, negative-control outcomes and synthetic counts in
   the job summary.

The guard itself has dependency-free Python tests for step ordering,
shell syntax and unsafe environment refusal. The tests prove that an
invalid context is rejected **before the first Docker invocation**.

## Important limits

- This validates preserving synthetic rows across **idempotent rerun**,
  not actual upgrade from prior tagged Flind installations.
- The marker tables are independent of product events, API sessions, and
  object-storage references. Their preservation does not guarantee that
  all domain tables, user settings, tenant ACLs or analytics data survive.
- No production or customer database is accessed. No backup artifact
  leaves the ephemeral GitHub runner. The separate PostgreSQL restore
  gate is documented in F4_SYNTHETIC_POSTGRES_RESTORE_GATE.md.
- Real upgrades with existing complex datasets, recovery across services,
  and full independent installation remain release blockers.
- No publishing, GitHub Release, package, tag or production deployment
  without explicit `GREEN LIGHT FLIND`.
