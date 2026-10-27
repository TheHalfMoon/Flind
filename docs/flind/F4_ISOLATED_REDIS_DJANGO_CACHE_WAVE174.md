# Flind Wave 174 — First-party Django cache qualified against isolated Redis 8.10.2

## Real integration (27 October 2026)

**PASS**: pinned real private Flind source commit `1905e9afb0f25f2685f042485b59f4c433403ffe` booted Django 5.2.18 from locally verified Git Python blobs, then executed the **actual Django default cache** against **real Redis 8.10.2**. 116 Django apps registered. Test data was wholly synthetic and scoped to one disposable Redis instance on the authorized Mac; this is *not* production/user data.

The Redis server was started with `port 0` (**no TCP listener**), Unix socket `/private/tmp/flind-wave174-redis/redis.sock` (permissions 700), `save ""`, `appendonly no`, `maxmemory 32mb`, and `maxmemory-policy noeviction`. The temporary directory contains the explicit marker `.flind-redis-scratch-v1`. Existing Redis/other systems and their databases were never targeted.

The new `tools/flind/qualify_isolated_redis_wave174.py` **fails closed before imports/network** if a private source checkout, scratch marker, or Unix socket is absent, symlinked, outside `/private/tmp`, or overlapping. It verifies the source commit offline without lazy Git blob fetching. It allows only the exact temporary Redis Unix socket at the Python socket layer, refusing TCP and unrelated Unix sockets; it validates live Redis `port=0`, no AOF, no RDB snapshot schedule, correct data dir and bounded max memory.

## Executed checks

The tested proposed source reported:
```json
{
  "django_registry_qualified": true,
  "registered_apps": 116,
  "redis_unix_socket_only": true,
  "redis_direct_protocol_qualified": true,
  "django_cache_qualified": true,
  "ttl_qualified": true,
  "expiration_qualified": true,
  "synthetic_cache_keys_observed": 2,
  "celery_worker_qualified": false,
  "tenant_auth_isolation_qualified": false,
  "ingestion_qualified": false,
  "release_qualified": false
}
```

- Real first-party `settings.CACHES["default"]["LOCATION"]` was confirmed to be this exact Redis Unix URL.
- Django default cache stored and retrieved **two distinct synthetic dictionaries**, verified backend TTL values in the 1–20 second budget, set a 1-second expiry key and independently verified it had expired after 1.4 seconds.
- Synthetic test keys were explicitly deleted in `finally`.
- The actual Redis service's startup reports it accepts **Unix connections only**.
- Wave174 safety/admission regression tests: **8/8 PASS**; tests never connect to an outside service.
- During Django startup, some legacy background task hooks attempted Celery operations over a different socket/destination. These were **blocked** and logged, and did not make the cache tests fail. Redis showed an additional scratch key after the run; it was not interpreted as a tenant/user-isolation result, and the entire disposable server will be stopped/cleaned. **Neither Celery nor background workers have been qualified.**

## Scope and next release blockers

Django registry PASS, real isolated Redis default cache PASS and real TTL/expiry PASS. These do **not** establish safe tenant identity/authorization, a Celery worker, queues, durable ingestion, real Kafka/ClickHouse, SDK event delivery, tenant-filtered API queries, dashboard/browser/desktop flows or release readiness. Current-main Django registry and scoped isolated PostgreSQL smoke were previously qualified in Waves171–173, but **full migration application/rollback remains unqualified**. OAuth issuer/PKCE and all first-party product/distribution identity gates (#82/#5) remain open.

Repo PRIVATE, inherited GitHub Actions disabled, no publishing/deployment/paid models or compute. All legally required third-party attribution remains unchanged.
