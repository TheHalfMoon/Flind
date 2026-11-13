# Synthetic ClickHouse Native export and restore gate

Status: **not qualified until the exact-head real-service GitHub workflow passes**.

A PostgreSQL full custom-format backup/restore gate exists separately.
This test introduces a limited ClickHouse data export/import proof for three
synthetic tenant markers, not a production backup or full database restore.

## Method

On an explicitly selected, ephemeral GitHub Actions run using the existing
real PostgreSQL, ClickHouse, Kafka and Redis migration stack:

1. Reject any non-ephemeral context, unexpected database endpoints, absent
   opt-in, wrong development settings, preexisting proof tables or unexpected
   runner directories before attempting a database write.
2. Use ClickHouse 26 and create a fresh temporary MergeTree table with three
   distinct synthetic tenant identifiers, markers, and integer values.
3. Export ordered rows as real binary `FORMAT Native` into a temporary
   runner-only file, confirm it is nonempty, import using a separate newly
   created table with the same schema, and require exact ordered row parity.
4. Insert an extra synthetic row into the imported copy. A byte-for-byte
   comparison with the source **must reject it**. Truncate the disposable
   restored table, import the identical saved Native data again, and require
   parity a second time.
5. Delete only the two disposable test tables and the temporary local binary
   file, even if verification fails. Fail closed if cleanup cannot complete.
6. Report only the archive byte length, SHA256 digest, test outcome and
   explicit non-qualification flags in the job summary. No backup artifact
   or tenant rows are uploaded.

This additional work executes only on the isolated
`flind-ci/clickhouse-recovery-*` branch or with a manual
`clickhouse_recovery=true` input on
`.github/workflows/flind-runtime-migrations.yml`.

Local validation: `bash -n` and
`python3 -m unittest tools.flind.test_clickhouse_native_recovery -v`
test source shape and unsafe-context denial using a fake Docker trap.
They **do not** prove an actual ClickHouse import.

## Still required

This is only **table-level logical export and import**. It does not include
the schema archive, projections/materialized views, replication metadata,
shards, distributed DDL, ClickHouse's proper BACKUP/RESTORE command,
production storage snapshot, Kafka offsets, files, or cross-service
consistency. Production recovery RPO/RTO and real upgrade-from-previous-
release tests remain unqualified. Preserve upstream legal notices.

Release state: **NO-GO**. No package, GitHub Release, service,
distribution or tag without the founder's explicit `GREEN LIGHT FLIND`.
