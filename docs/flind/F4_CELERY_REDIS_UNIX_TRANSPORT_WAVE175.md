# Flind Wave 175 — Correct Celery/Kombu Redis Unix-socket transport

## Source bug and minimal patch

The Flind Django cache supports `REDIS_URL=unix:///path/to/redis.sock?db=0`, but inherited `posthog/settings/celery.py` directly assigned this URL to `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`. The tested installed Kombu transport registry refuses this scheme with **`KeyError: No such transport: unix`**. When the Wave174 integration enabled Django caching via Unix Redis, app-startup Celery task hooks attempted an unauthorized connection and were blocked rather than sent to the designated scratch Redis.

Wave175 adds the pure `flind_celery_redis_url()` mapping to `posthog/settings/celery.py`. It transforms **only** Django's local `unix:///` URL prefix into Kombu's `redis+socket:///` transport syntax and leaves `redis://`, `rediss://`, existing `redis+socket://` and other URL schemes unchanged. Both Celery broker and result-backend settings use it. The default TCP/TLS Redis behavior and other services are unaffected. Internal inherited source package paths stay intact until qualified migration; third-party attribution is not removed.

## Real first-party runtime qualification — 2026-10-27

On authorized Mac, a disposable, explicitly marked Redis **8.10.2** scratch server was started in `/private/tmp/flind-wave175-celery-redis`, **port=0** (no TCP), Unix socket permissions 700, RDB/AOF persistence disabled, max memory 32MiB. Existing Redis and PostgreSQL were not touched. The pinned private Flind source at `1905e9afb0f25f2685f042485b59f4c433403ffe` was used with the **exact proposed modified Celery settings module staged only in its disposable source checkout**, plus Git-hash-verified original `posthog/__init__.py` and `posthog/settings/__init__.py` so Python could correctly import the full Django settings instead of accidentally treating sparse directories as namespace packages.

Actual checks:
- Real original Kombu `Connection("unix:///...")` was rejected. `Connection("redis+socket:///...")` **connected** and opened a real Redis-backed channel.
- Django `django.setup()` **PASS, 116 registered apps** and the first-party settings supplied **exactly the owned scratch `redis+socket://` broker and result-backend URL**.
- A real synthetic message was **published and consumed/ACKed** via `kombu.Connection.SimpleQueue` on the scratch Redis broker; its queue was cleared.
- The real Celery `RedisBackend` **stored, read back and forgot** a synthetic SUCCESS result containing `{"synthetic": true, "wave": 175}`.
- Django app-startup `sync_mcp_server_templates` was observed being queued to this isolated scratch Redis rather than failing on an unsupported Redis transport. No worker was started and none of these app background tasks executed.
- The exact proposed executable `tools/flind/qualify_celery_redis_unix_wave175.py` completed **exit 0**, reporting `celery_broker_configuration_qualified=true`, `celery_broker_roundtrip_qualified=true`, `celery_result_backend_qualified=true`, `django_registry_qualified=true`.
- **8/8 focused unit tests PASS** for normal TCP/TLS Redis URL preservation, allowed Unix mapping, unsupported host-form refusal, both config assignments, actual Kombu transport recognition, negative unsupported transport and query preservation. No new dependencies, paid resources, deployment or publication.

The executable requires Wave174's marked Redis admission/single Unix socket allowlist and live Redis no-persistence/no-TCP/limited-memory checks. It uses only synthetic data. Existing Flind worker and event ingestion remain **unqualified**: synthetic Kombu queue publish/consume does not mean a production Celery worker processed a real product job.

## Remaining release gates

Full 839-migration apply+rollback on isolated PostgreSQL, real worker execution/retry/lock/recovery, Kafka/ClickHouse ingestion from the Flind SDK through tenant-scoped API/dashboard, browser/desktop E2E, live owner-controlled OAuth/PKCE/JWKS, final source/package/SDK/artifact naming audit, and legal notice verification are all still pending. **#82 and #5 stay OPEN; release NO-GO.**

Private repo, inherited GitHub Actions disabled. No publication, deployment, paid compute/models, customer data, or shared databases. Preserve mandatory third-party attribution.
