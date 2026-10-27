#!/usr/bin/env python3
"""First-party Flind Celery broker/result smoke against marked Unix-socket-only Redis.

Runs a disposable synthetic Kombu publish/consume and Celery result roundtrip.
This does not start a worker or qualify tenant auth, ingestion, or release.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time


def qualify(source: Path, redis_dir: Path, ref: str = "HEAD") -> dict[str, object]:
    result: dict[str, object] = {
        "phase": "first-party-celery-redis-unix-broker",
        "source_ref": ref,
        "django_registry_qualified": False,
        "celery_broker_configuration_qualified": False,
        "celery_broker_roundtrip_qualified": False,
        "celery_result_backend_qualified": False,
        "real_worker_qualified": False,
        "tenant_auth_isolation_qualified": False,
        "ingestion_qualified": False,
        "release_qualified": False,
    }
    started = time.monotonic()
    try:
        sys.path.insert(0, str(source))
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from tools.flind.qualify_isolated_redis_wave174 import admitted, restricted_sockets
        from tools.flind.qualify_sparse_django_registry_wave147 import (
            GitTrackedPythonFinder, GitBlobBatchReader, git_offline_env,
            index_tracked_python,
        )
        import re
        import subprocess
        if not admitted(source, redis_dir, ref):
            raise ValueError("unmarked_redis_source_or_socket")
        signal.alarm(130)
        sha = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "--verify", ref + "^{commit}"],
            capture_output=True, check=False, timeout=20, env=git_offline_env(),
        )
        resolved = sha.stdout.decode("ascii").strip()
        if sha.returncode or len(resolved) not in (40, 64) or not re.fullmatch("[a-f0-9]+", resolved):
            raise ValueError("unverified_first_party_source")
        result["source_commit"] = resolved
        endpoint = str(redis_dir / "redis.sock")
        restricted_sockets(endpoint)
        import redis
        client = redis.Redis(
            unix_socket_path=endpoint, db=0, decode_responses=True,
            socket_connect_timeout=3, socket_timeout=3,
        )
        try:
            if not client.ping():
                raise RuntimeError("scratch_redis_unavailable")
            redis_config = client.config_get()
            if (int(redis_config.get("port", -1)) != 0
                    or Path(redis_config.get("dir", "")).resolve() != redis_dir.resolve()
                    or redis_config.get("appendonly") != "no"
                    or redis_config.get("save") != ""
                    or not 0 < int(redis_config.get("maxmemory", 0)) <= 64 * 1024 * 1024):
                raise ValueError("redis_not_ephemeral_or_bounded")
            url = f"redis+socket://{endpoint}?db=0"
            os.environ.update({
                "DJANGO_SETTINGS_MODULE": "posthog.settings",
                "SECRET_KEY": "flind_wave175_ephemeral_synthetic_only",
                "DATABASE_URL": "postgresql://no_user:no_password@127.0.0.1:65433/flind_nonexistent",
                "POSTHOG_DB_NAME": "flind_nonexistent",
                "REDIS_URL": f"unix://{endpoint}?db=0",
                "CLICKHOUSE_HOST": "127.0.0.1",
                "CLICKHOUSE_PORT": "65435",
                "KAFKA_HOSTS": "127.0.0.1:65437",
                "DISABLE_MMDB": "true",
                "PYTHONDONTWRITEBYTECODE": "1",
            })
            tracked = index_tracked_python(source, ref)
            with GitBlobBatchReader(source, ref) as batch:
                sys.meta_path.append(GitTrackedPythonFinder(
                    source, ref, tracked, limit=2700, deadline=115, batch_reader=batch,
                ))
                import django
                django.setup()
                from django.apps import apps
                from django.conf import settings
                result["django_registry_qualified"] = True
                result["registered_apps"] = len(apps.get_app_configs())
                if settings.CELERY_BROKER_URL != url or settings.CELERY_RESULT_BACKEND != url:
                    raise ValueError("unexpected_celery_redis_destination")
                result["celery_broker_configuration_qualified"] = True
                from kombu import Connection
                with Connection(url, connect_timeout=3) as connection:
                    connection.connect()
                    queue = connection.SimpleQueue("flind.wave175.synthetic")
                    try:
                        queue.put({"synthetic": True, "wave": 175})
                        msg = queue.get(block=True, timeout=5)
                        if msg.payload != {"synthetic": True, "wave": 175}:
                            raise RuntimeError("celery_broker_payload_mismatch")
                        msg.ack()
                        result["celery_broker_roundtrip_qualified"] = True
                    finally:
                        queue.clear()
                        queue.close()
                from celery import Celery
                synthetic = Celery("flind_wave175_synthetic", broker=url, backend=url)
                task_id = "flind-wave175-synthetic-result"
                try:
                    synthetic.backend.store_result(
                        task_id, {"synthetic": True, "wave": 175}, state="SUCCESS",
                    )
                    metadata = synthetic.backend.get_task_meta(task_id)
                    if (metadata.get("status") != "SUCCESS"
                            or metadata.get("result") != {"synthetic": True, "wave": 175}):
                        raise RuntimeError("celery_result_roundtrip_failed")
                    result["celery_result_backend_qualified"] = True
                finally:
                    synthetic.backend.forget(task_id)
        finally:
            client.close()
    except Exception as exc:
        result["blocker"] = type(exc).__name__
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 1)
        signal.alarm(0)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--redis-dir", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args()
    report = qualify(options.root, options.redis_dir, ref=options.ref)
    if options.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print("Flind Celery broker:", "PASS" if "blocker" not in report else "BLOCKED")
    return 0 if (
        "blocker" not in report and report["celery_broker_roundtrip_qualified"]
        and report["celery_result_backend_qualified"]
    ) else 2


if __name__ == "__main__":
    sys.exit(main())
