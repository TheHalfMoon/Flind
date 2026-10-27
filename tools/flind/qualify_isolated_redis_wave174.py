#!/usr/bin/env python3
"""Read-only first-party Flind source plus dedicated Redis Unix-socket cache probe.

Never uses a production Redis or database; never certifies Celery, tenancy,
ingestion, Kafka, ClickHouse, migration execution, or release.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time

MARKER = ".flind-redis-scratch-v1"
MARKER_TEXT = "FLIND_REDIS_SCRATCH_V1\n"
SAFE_REF = re.compile(r"[A-Za-z0-9_./-]{1,128}\Z")
TEST_KEYS = ("flind-wave174:synthetic:tenant-a:123", "flind-wave174:synthetic:tenant-b:123",
             "flind-wave174:synthetic:expires")
ROOT = Path("/private/tmp")


def admitted(source: Path, redis_dir: Path, ref: str) -> bool:
    """Admit only a marked scratch Redis socket, never a shared Redis server."""
    try:
        if not SAFE_REF.fullmatch(ref) or ref.startswith("-") or ".." in ref.split("/"):
            return False
        sandbox = ROOT.resolve()
        if any(p.is_symlink() or not p.is_dir() or sandbox not in p.resolve().parents
               for p in (source, redis_dir)):
            return False
        if not (source / ".git").exists() or not (source / "pyproject.toml").is_file():
            return False
        if (redis_dir / MARKER).is_symlink() or (redis_dir / MARKER).read_text() != MARKER_TEXT:
            return False
        endpoint = redis_dir / "redis.sock"
        if endpoint.is_symlink() or not endpoint.is_socket():
            return False
        if source.resolve() == redis_dir.resolve() or source.resolve() in redis_dir.resolve().parents:
            return False
        if redis_dir.resolve() in source.resolve().parents:
            return False
        return True
    except (OSError, ValueError, UnicodeError):
        return False


def restricted_sockets(endpoint: str) -> None:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def connect(sock, address):
        if sock.family == socket.AF_UNIX and address == endpoint:
            return original_connect(sock, address)
        raise OSError("Flind scratch Redis allows only its own Unix socket")

    def connect_ex(sock, address):
        if sock.family == socket.AF_UNIX and address == endpoint:
            return original_connect_ex(sock, address)
        raise OSError("Flind scratch Redis denies non-scratch sockets")

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex

    def reject_tcp(*args, **kwargs):
        raise OSError("Flind isolated Redis does not allow TCP")

    socket.create_connection = reject_tcp


def qualify(source: Path, redis_dir: Path, ref: str = "HEAD") -> dict[str, object]:
    report: dict[str, object] = {
        "phase": "first-party-django-isolated-redis-cache",
        "source_ref": ref,
        "django_registry_qualified": False,
        "redis_unix_socket_only": False,
        "redis_direct_protocol_qualified": False,
        "django_cache_qualified": False,
        "ttl_qualified": False,
        "expiration_qualified": False,
        "celery_worker_qualified": False,
        "tenant_auth_isolation_qualified": False,
        "ingestion_qualified": False,
        "release_qualified": False,
    }
    start = time.monotonic()
    try:
        if not admitted(source, redis_dir, ref):
            raise ValueError("unmarked_or_unsafe_scratch_redis")
        signal.alarm(115)
        sys.path.insert(0, str(source))
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from tools.flind.qualify_sparse_django_registry_wave147 import (
            git_offline_env, index_tracked_python, GitBlobBatchReader, GitTrackedPythonFinder,
        )
        sha_process = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "--verify", ref + "^{commit}"],
            capture_output=True, check=False, timeout=20, env=git_offline_env(),
        )
        sha = sha_process.stdout.decode("ascii").strip()
        if sha_process.returncode or len(sha) not in (40, 64) or not re.fullmatch(r"[a-f0-9]+", sha):
            raise ValueError("unverified_first_party_source")
        report["source_commit"] = sha
        endpoint = str(redis_dir / "redis.sock")
        restricted_sockets(endpoint)
        import redis
        client = redis.Redis(unix_socket_path=endpoint, db=0, decode_responses=True,
                             socket_connect_timeout=3, socket_timeout=3)
        try:
            if not client.ping():
                raise RuntimeError("scratch_redis_ping_failed")
            config = client.config_get()
            if (int(config.get("port", -1)) != 0
                    or Path(config.get("dir", "")).resolve() != redis_dir.resolve()
                    or config.get("appendonly") != "no"
                    or config.get("save") != ""
                    or not 0 < int(config.get("maxmemory", 0)) <= 64 * 1024 * 1024):
                raise ValueError("redis_configuration_not_isolated")
            report["redis_unix_socket_only"] = True
            report["redis_direct_protocol_qualified"] = True
            tracked = index_tracked_python(source, ref)
            os.environ.update({
                "DJANGO_SETTINGS_MODULE": "posthog.settings",
                "SECRET_KEY": "flind_wave174_ephemeral_synthetic_only",
                "DATABASE_URL": "postgresql://no_user:no_password@127.0.0.1:65433/flind_nonexistent",
                "POSTHOG_DB_NAME": "flind_nonexistent",
                "REDIS_URL": f"unix://{endpoint}?db=0",
                "CLICKHOUSE_HOST": "127.0.0.1",
                "CLICKHOUSE_PORT": "65435",
                "KAFKA_HOSTS": "127.0.0.1:65437",
                "DISABLE_MMDB": "true",
                "PYTHONDONTWRITEBYTECODE": "1",
            })
            with GitBlobBatchReader(source, ref) as batch:
                finder = GitTrackedPythonFinder(
                    source, ref, tracked, limit=2700, deadline=105, batch_reader=batch,
                )
                sys.meta_path.append(finder)
                import django
                django.setup()
                from django.apps import apps
                report["django_registry_qualified"] = True
                report["registered_apps"] = len(apps.get_app_configs())
                from django.conf import settings
                if settings.CACHES["default"]["LOCATION"] != f"unix://{endpoint}?db=0":
                    raise ValueError("unexpected_django_cache_destination")
                from django.core.cache import caches
                cache = caches["default"]
                a, b, exp = TEST_KEYS
                try:
                    cache.set(a, {"synthetic": True, "value": 17}, timeout=20)
                    cache.set(b, {"synthetic": True, "value": 29}, timeout=20)
                    if (cache.get(a) != {"synthetic": True, "value": 17}
                            or cache.get(b) != {"synthetic": True, "value": 29}):
                        raise RuntimeError("django_cache_roundtrip_failed")
                    report["django_cache_qualified"] = True
                    found_keys = list(client.scan_iter(match="*flind-wave174:synthetic:*", count=100))
                    valid_ttls = [client.ttl(key) for key in found_keys]
                    if len(found_keys) < 2 or not all(0 < ttl <= 20 for ttl in valid_ttls):
                        raise RuntimeError("redis_ttl_not_observed")
                    report["ttl_qualified"] = True
                    cache.set(exp, "temporary", timeout=1)
                    time.sleep(1.4)
                    if cache.get(exp) is not None:
                        raise RuntimeError("cache_expiry_not_observed")
                    report["expiration_qualified"] = True
                    report["synthetic_cache_keys_observed"] = len(found_keys)
                finally:
                    cache.delete_many(TEST_KEYS)
                    cache.close()
        finally:
            client.close()
    except Exception as exc:
        report["blocker"] = type(exc).__name__
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - start, 1)
        signal.alarm(0)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--redis-dir", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    outcome = qualify(args.root, args.redis_dir, ref=args.ref)
    if args.json:
        print(json.dumps(outcome, indent=2, sort_keys=True))
    else:
        print("Flind isolated Django/Redis cache:", "PASS" if "blocker" not in outcome else "BLOCKED")
    return 0 if "blocker" not in outcome and outcome["expiration_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
