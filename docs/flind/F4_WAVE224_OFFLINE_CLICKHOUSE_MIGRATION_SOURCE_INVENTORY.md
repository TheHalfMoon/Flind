# Wave 224 — source-only original ClickHouse migration inventory

**Scope:** offline Git provenance, not a ClickHouse migration plan, schema migration, native Kafka/Rust/Node E2E, or release proof.

## Motivation

The original `posthog/management/commands/migrate_clickhouse.py` calls `_create_database_if_not_exists` and `_create_migration_tracking_tables_if_not_exist` **before** evaluating its `--plan` and `--check` options. Therefore the original `migrate_clickhouse --plan` command is not guaranteed to be read-only and must not be pointed at an unverified or shared ClickHouse server for a harmless-looking inventory.

The original `print_ch_migration_sql` management command is described as offline but imports each migration module. This new inventory does **not import or execute** migration modules and only uses Git's committed tree and blob metadata.

## Why the SQL sidecars are mandatory source dependencies

The original `0238_align_ws_events_kafka_mv_with_msk.py` resolves `sql/0238` relative to its own `__file__` and reads `us_kafka.sql` + `us_mv.sql` for `RunMode.CLOUD_US`, or `eu_kafka.sql` + `eu_mv.sql` for `RunMode.CLOUD_EU`. These are region-specific baked DDL inputs. A Python-only source digest would miss actual changes to cloud migration behavior. Wave224 **never executes or imports** this module, but includes its four SQL assets as Git blob provenance.

## Entry point and guarantees

`python tools/flind/e2e/offline_clickhouse_migration_inventory_wave224.py --root . --ref HEAD --json`

The tool resolves an immutable 40-hex Git commit, enumerates original Python migration modules **and nested `.sql` assets** from the Git tree. It separates canonical four-digit Python modules from historical noncanonical Python names (including `0067_event_kafka_debug_table copy.py`), checks every selected local Python and SQL Git blob against immutable tree sizes using `git cat-file --batch-check`, and hashes the combined Python+SQL source set. This includes the four original `sql/0238/{eu,us}_{kafka,mv}.sql` assets: excluding these would let DDL changes escape the migration provenance digest. The receipt reports SQL counts, paths and bytes separately from Python modules.

It rejects symlinked Python or SQL migration sources, path escapes, invalid modes, unsafe Git refs, missing objects and exceeding bounded source sizes. Git explicitly disables lazy-promisor fetching and prompts; the only Git verbs issued are `rev-parse`, `ls-tree` and `cat-file`. No Python migrations are imported, no SQL is generated, no network/Docker/app service is contacted, and no Git objects are materialized into the checkout. Its output always leaves `clickhouse_schema_qualified`, `migrations_applied_qualified`, `native_ingestion_e2e_qualified` and `release_qualified` **false**.

## Executed evidence

On a standalone local Python interpreter with real local Git fixture repositories, `test_offline_clickhouse_migration_inventory_wave224.py` passed **15/15** unit tests. Test cases cover source fingerprint reproducibility despite dirty worktree, observed read-only Git commands with lazy fetching disabled, symlink rejection, unsafe ref rejection, a legacy noncanonical filename and refusal to call a Git write operation, missing local Git/promisor blob rejection, refusal of an empty canonical inventory, missing historical noncanonical Git object rejection, and Git-tree/object size mismatch rejection, committed historical Python and SQL edits updating the manifest, missing SQL Git blob refusal, SQL symlink refusal, plus actual CLI JSON success and invalid-reference exit-code validation. Both modules compiled via `py_compile`. The exact 8,227-byte source and 11,883-byte test files were executed in the isolated sandbox and their `git hash-object` values matched the private GitHub PR branch blobs (`1fb777527c46d307a04f90f1489db6bad43b4b80` and `03a742b7511b0f46f733d7fecee844701ef407f2`); no lines exceeded the 120-character line budget.

## Immutable first-party source evidence (remote GitHub, not local checkout)

Authenticated GitHub Git-tree traversal of **merged main** commit `a5585565391734d7948f7e3a6b816e35eca7db09` resolved the original migration subtree `23ea2f226e6be4f2caca554b6ef7cd769d61baa0` (not truncated). Its **350** attested migration source entries comprise **345 canonical Python**, **1 historical noncanonical Python** and **4 nested SQL assets**. Python files total **406,051 bytes**; SQL assets **76,714 bytes**; combined **482,765 bytes**. Top-level Contents API SHA/size metadata matched Git-tree entries; four representative Git blobs (first, last, historical, largest) were fetched and matched their tree sizes. All selected entries have regular Git blob modes and satisfy the source-size budget.

The Wave224 Python+SQL manifest SHA256 for that immutable source tree is `018b6117524c82a594fb8d5f7ff0cd695fbbff34ca3a9b5c0d2758570ccf8c6f`, computed from sorted full paths and Git blob IDs with NUL separators. Evidence: `docs/flind/receipts/wave224-first-party-github-source-tree-350-assets.json`. Isolated fixture evidence: `docs/flind/receipts/wave224-clickhouse-git-fixtures-15-tests.json`.

**This is first-party remote GitHub metadata evidence, NOT a run of the offline Git audit on a complete local Flind checkout.** The 350 original blob objects have not all been checked for local availability; only four were individually fetched for spot-checking. The full original migration runner and ClickHouse schemas have not been exercised.

The original 15 real-Git-fixture tests were independently rerun on the exact GitHub-blob-matching implementation and test modules: **15/15 PASS in Python 3.13.5** and **15/15 PASS under `python -O`**; Python compilation PASS. All runs are read-only with respect to Flind source data and connect to no production services. These focused results qualify the **tool code for inclusion in private main**, not the original ClickHouse migration inventory or a release.

**The full private Flind checkout has NOT been audited by the offline Git tool.** Desktop Commander reached its monthly cap; the actual source inventory count/manifest must still be reproduced from a complete owner-verified local Git checkout before declaring the original migration source inventory qualified. Complete repo lint/test gates also remain outstanding. The earlier real Wave222 PostgreSQL smoke passed; it does not qualify full PostgreSQL or ClickHouse migrations. The original Wave216 joined service Jest remains **4/4 failing** because complete schemas are missing. Release **NO-GO**.

No publication, deployment, paid services or customer/other-project data access; retain private Flind repository and disabled GitHub Actions.
