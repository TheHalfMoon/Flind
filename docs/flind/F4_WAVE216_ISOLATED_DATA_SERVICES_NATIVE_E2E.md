# Flind Wave 216 - isolated services and original service E2E evidence

## Local isolated services

Docker Desktop 29.8.2 was started. The pre-existing Zyara PostgreSQL
container was not changed. The standalone flindwave216 Compose project
started separate, healthy, loopback-only PostgreSQL 16 on 15439, Redis 7
on 16380, and ClickHouse 25.8 on 18124. Compose config and ownership
probe succeeded. PostgreSQL has four freshly created test databases,
ClickHouse uses unique flind_test_wave216abc123 test database with local
throwaway credentials. Synthetic two-tenant events were written,
read separately and the isolated probe table deleted. This proves
the data engine smoke checks, not full application ingestion.

The isolated Rust/Node service admission now supports authenticated
ClickHouse credentials. 8/8 independent Node24 admission tests passed.

## Actual original Rust/Node service E2E

Ephemeral genuine Kafka 4.3.1 started on 127.0.0.1:19093. Kafka native
publish/consume passed. The unchanged first-party Rust/Node service Jest
runner accepted the disposable sandbox in dry-run.

The actual first-party service E2E was invoked, and FAILED all 4 service
cases (1 Jest suite FAILED, exit 1). PostgreSQL test_posthog had no
posthog_cohort, posthog_team, posthog_user or posthog_organization tables.
ClickHouse had no sharded_events, person, person_distinct_id or
events_dead_letter_queue tables. The original database migration setup
is missing. No synthetic replacement schema was supplied.

An ownership-verified, read-only original schema preflight now rejects
unmigrated services before starting the expensive destructive E2E again.
Four independent Python tests of that gate PASSED, including rejection
of foreign containers and non-loopback ports.

## Qualification decision

Full Kafka to original Rust to production Node joined analytics to
durable ClickHouse has NOT passed. Next: isolated original migrations,
rerun the first-party service Jest, then Django tenant/auth and SDK/
browser E2E. Release NO-GO. Repo PRIVATE, Actions disabled, no paid
services, production data, deployment or publication.
