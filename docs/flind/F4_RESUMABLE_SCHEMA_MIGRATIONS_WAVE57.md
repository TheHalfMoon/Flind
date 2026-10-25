# Wave 57 — Resume bounded migrations within one disposable database

## Background

Wave 55 migration attempts against separately created PostgreSQL clusters
committed 2,541 and 2,610 migration records, but exceeded the bounded
execution limit and discarded the entire temporary database afterward.
This made every attempt replay the same initial schema work.

Wave 56 proved that the smaller Django contenttypes migration subset
can finish in an isolated PostgreSQL instance. This wave tries a more
useful strategy for the full migration graph without relaxing safety.

## Implementation

- Keep **one** newly created, SCRAM-authenticated disposable PostgreSQL
  cluster during up to three bounded migration subprocess invocations.
  The connection is random localhost-only and cannot touch the global
  PostgreSQL service or another project.
- Allow the real Django migration recorder to keep previously committed
  rows across attempts within that one temporary test run. No fake,
  skip, force, SQL patch or bypass is used.
- After every round, independently query the committed migration count
  and last committed migration name from the isolated cluster.
- Retry only when the process reached the time guard **and** additional
  migration records were committed. Stop if there was no progress,
  an unexpected error or a regressing receipt.
- Bound invocations to 1..3, each with a time cap 20..120 seconds and the
  Wave55 per-process free-disk safety threshold.
- As before, a transient one-use SECRET_KEY, loopback placeholders for
  non-PostgreSQL services and zero inherited provider credentials are used.
- No temporary databases, background services or migration processes
  are allowed to persist after the outer cluster callback returns.

Reproduction under the separate frozen Python 3.14.7 environment:

    python tools/flind/qualify_resumable_migrations_wave57.py \
      --json --rounds 2 --seconds 112

## Qualification rules

Full schema qualified only when the real Django migrate subprocess
**exits successfully** with positive migration-row evidence, and the
owned PostgreSQL cluster has passed its component smoke. Any other
result is NO-GO, even if thousands of migration rows were committed.

Even full schema success is not launch/release qualification: SDK
capture, Kafka/Celery, ClickHouse query readback, auth/tenant isolation,
frontend builds and device/browser E2E remain separate blockers.

## Executed evidence, October 25, 2026

Native, same-cluster attempt: two rounds at 112 seconds each.

| Round | Migration records in disposable DB | Newly committed | Django command success |
|---|---:|---:|---|
| 1 | 2,477 | 2,477 | No, bounded timeout |
| 2 | 2,596 | 119 | No, bounded timeout |

- The second run resumed from committed state in the same private DB.
  This demonstrates real forward progress without replaying all initial
  migrations, but does NOT show that the entire Flind schema works.
- Last recorded committed migration in the second round:
  actions.0002_alter_action_created_by_alter_action_events_and_more.
- Blocker: Bounded migration rounds exhausted. Overall exit code 2.
  full_schema_migrations_completed=false; release_qualified=false.
- Private PostgreSQL process was stopped and all temporary schema
  files were cleaned after the receipt was obtained.
- Disk free after the run was about 3.8 GiB, so another expensive
  migration run is not authorized by the current conservative
  resource plan. Review current disk allocation first.
- Focused retry/guardrail tests: 7/7 PASS; full Flind Python suite: 437/437 PASS.

This also explains why earlier independent runs varied in last
migration/record count. The migration recorder contains several apps,
and the last committed record does not necessarily identify the
migration currently consuming CPU.

## Pending qualification

The remaining migration graph, dependencies and post-migrate startup
effects must be completed on a resource-safe isolated runner, followed
by actual Django API/SDK->Kafka/ClickHouse data readback,
authorization and device/browser E2E. No release claims are made.
