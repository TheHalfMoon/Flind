# Wave 176 — Actual isolated Celery worker, task result, and retry

## Actual cross-process worker test on 2026-10-27

The Wave175 first-party Celery configuration fix verified a real Redis Unix-socket broker and result backend, but no worker had executed a task. Wave176 takes the next limited step: one **real Celery solo worker process** executes two **synthetic fixture tasks** received through a dedicated queue on a scratch **Redis 8.10.2** instance.

**Executed against an authorized Mac using existing Python/Celery and no paid services**:

- Redis socket: `/private/tmp/flind-wave175-celery-redis/redis.sock`, with `port=0`, no RDB/AOF persistence, max 32MiB memory. This server was created specifically for synthetic Flind qualification, not shared/production Redis.
- Worker scratch: `/private/tmp/flind-wave176-worker-scratch`; explicit `.flind-worker-scratch-v1` marker.
- Worker uses **`--pool=solo --concurrency=1`**, listens **only** to `flind_wave176_synthetic`, disables gossip/mingle/heartbeat, and loads only the two test fixture tasks. No first-party job handlers, customer data or production systems were imported into the worker.
- Synthetic echo task: request `73` → result `{"synthetic": true, "value": 73}`, state **SUCCESS**.
- Synthetic retry task: first attempt called `self.retry(countdown=0)`; next attempt returned `{"synthetic": true, "retries": 1}`, state **SUCCESS**. This is an actual queue-delivered retry, not a mocked retry.
- Both task results were retrieved through the Redis result backend, checked and forgotten.
- The **exact proposed reusable executable** `tools/flind/qualify_synthetic_celery_worker_wave176.py` ran with exit code **0**, reporting `real_synthetic_worker_started=true`, `synthetic_queue_roundtrip_qualified=true`, `synthetic_retry_qualified=true`, `result_backend_qualified=true`, **`worker_stopped=true`**. It started and stopped its worker child process automatically.
- **9/9 focused Python unit tests PASS**, under `-W error::ResourceWarning`, validating private scratch markers, Unix socket type, directory separation/symlink refusal, bounded deadlines, synthetic-only registration and false release flags.

## Reproduction

Only on an authorized disposable machine with a separately created, explicitly marked scratch Redis server listening **solely over its private Unix socket**. No shared Redis or production services:

```sh
printf 'FLIND_CELERY_WORKER_SCRATCH_V1\n' > /private/tmp/flind-wave176-worker-scratch/.flind-worker-scratch-v1

python tools/flind/qualify_synthetic_celery_worker_wave176.py \
  --redis-dir /private/tmp/flind-wave175-celery-redis \
  --worker-dir /private/tmp/flind-wave176-worker-scratch \
  --timeout 40 --json
```

The program preflights both source directories under `/private/tmp` and validates their exact scratch markers and Unix socket. It rejects symlinks and unsafe directories, ensures Redis `port=0`, no persistence, correct data directory and capped memory, restricts Python socket connections to that Unix path, starts the worker with a minimal environment and its own queue, stops/kills **only its own worker** on failure or success, and never treats synthetic tasks as first-party task/tenant/ingestion or release qualification. Do not run on another user's Redis instance.

## What this does and does not qualify

**Qualified in this wave:** the Redis Unix broker and result backend can connect a real isolated worker and successfully deliver, execute, ACK and retry independent synthetic tasks. This supports the Wave175 Celery Unix socket fix and closes the narrow *synthetic cross-process broker/worker smoke gate*.

**Not qualified:** actual Flind background workflows, persistence/recovery after Redis crash, replay/deduplication, tenant isolation, SDK→Kafka→ClickHouse→authenticated API→Dashboard/browser UI, full Django/PostgreSQL migrations and rollback, OAuth/PKCE, or final identity/distribution audit. Existing Wave171–175 results remain independently scoped. #82 and #5 remain OPEN; release NO-GO.

Private GitHub repository, inherited Actions disabled. No publication/deployment, paid compute/model, customer data or other service/data mutation. Retain mandatory third-party legal attribution.
