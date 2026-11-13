# Ephemeral Flind S3-compatible object export and restore gate

Status: **pending exact-head GitHub CI with real SeaweedFS**.

The existing Flind runtime migrations exercise PostgreSQL, ClickHouse,
Kafka and Redis. They have synthetic PostgreSQL restore and ClickHouse
Native-format export/import tests, but neither test covers objects stored
in the separately operated SeaweedFS S3-compatible service.

## Controlled execution

An opt-in workflow input `objectstorage_restore=true` or the explicitly
scoped `flind-ci/objectstorage-*` branch starts real SeaweedFS 4.29 in
the existing ephemeral GitHub runner **after the database migration
and synthetic data-preservation tests have passed**.

The test refuses to make an S3 request unless all of these match:
GitHub Actions, explicit synthetic opt-in, the exact checked-out repo,
existing runner temp and local evidence folder, `DEBUG=1`, canonical
development PostgreSQL URL, `http://127.0.0.1:19000` only, and valid
numeric run/attempt identity.

The test uses the preexisting dev credentials from the checked-in
`docker-compose.base.yml`, **not secrets or customer credentials**.
It creates a **freshly named bucket owned by the exact run** and
refuses to touch any existing matching bucket. It then:

1. Inserts two small, synthetic binary objects representing separate
   tenants with different bytes, and verifies each by S3 GET.
2. Saves those two bytestrings in an isolated `RUNNER_TEMP` directory.
3. Deletes only those two objects from its fresh test bucket, and
   requires HEAD to confirm they are gone.
4. Restores both objects from the previously exported files and requires
   byte-for-byte parity with the originals.
5. Corrupts only the second synthetic object, verifies the comparison
   detects that corruption, restores it again and verifies parity.
6. Deletes the two owned objects and the owned bucket in a cleanup block
   and deletes the runner-local archive files even if a test fails.
7. Prints **only** digest values, synthetic tenant count and success/
   non-qualification indicators in the job summary. No data or archive
   is uploaded as a GitHub Actions artifact.

## Local checks versus full proof

`python3 -m unittest tools.flind.test_qualify_objectstorage_synthetic_restore -v`
exercises the fail-closed guards (including a dozen rejected contexts),
byte-level corruption checks, and owned-object cleanup policy.
`python3 -m py_compile` checks Python syntax. These are **offline**
tests and do not prove any object was actually stored.

GitHub CI must pass the existing real migrations, start SeaweedFS,
execute actual signed S3 calls, and complete the negative controls.
If any step fails, keep the PR as a draft and diagnose it.

## Limits and mandatory release gates

This is a **small logical S3 export/import test**, not a filesystem or
SeaweedFS volume snapshot. It does not qualify lost volumes, replicated
masters, a full object namespace, cross-service backup consistency,
encryption-key recovery, recovery point/time objectives, disaster
recovery, object ACL/retention policies, or production customer data.

No public release, tag, app-store submission, deployment or package
distribution without the founder's explicit `GREEN LIGHT FLIND`.
Required legal/copyright/NOTICE provenance remains unchanged.
