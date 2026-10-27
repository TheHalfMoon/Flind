#!/usr/bin/env python3
"""Run an isolated synthetic Celery worker and verify task execution/retry.

No Flind product tasks, production workers, SQL, tenant data, or deployment.
Only a dedicated marked Redis Unix socket and marked private temporary directory.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

REDIS_MARKER = ".flind-redis-scratch-v1"
REDIS_MARKER_CONTENT = "FLIND_REDIS_SCRATCH_V1\n"
WORKER_MARKER = ".flind-worker-scratch-v1"
WORKER_MARKER_CONTENT = "FLIND_CELERY_WORKER_SCRATCH_V1\n"
QUEUE = "flind_wave176_synthetic"
ENV_REDIS = "FLIND_WAVE176_REDIS_DIR"
ENV_WORKER = "FLIND_WAVE176_WORKER_DIR"


def validate_scratch(redis_dir: Path, worker_dir: Path) -> bool:
    try:
        boundary = Path("/private/tmp").resolve()
        for p in (redis_dir, worker_dir):
            if p.is_symlink() or not p.is_dir() or boundary not in p.resolve().parents:
                return False
        if redis_dir.resolve() == worker_dir.resolve():
            return False
        for folder, marker, content in (
            (redis_dir, REDIS_MARKER, REDIS_MARKER_CONTENT),
            (worker_dir, WORKER_MARKER, WORKER_MARKER_CONTENT),
        ):
            file = folder / marker
            if file.is_symlink() or file.read_text() != content:
                return False
        sock = redis_dir / "redis.sock"
        return not sock.is_symlink() and sock.is_socket()
    except (OSError, UnicodeError, ValueError):
        return False


def restrict_connections(endpoint: str) -> None:
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def connect(sock, target):
        if sock.family == socket.AF_UNIX and target == endpoint:
            return real_connect(sock, target)
        raise OSError("Synthetic Flind worker forbids non-scratch connection")

    def connect_ex(sock, target):
        if sock.family == socket.AF_UNIX and target == endpoint:
            return real_connect_ex(sock, target)
        raise OSError("Synthetic Flind worker forbids non-scratch connection")

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex

    def deny_tcp(*args, **kwargs):
        raise OSError("Synthetic Flind worker forbids TCP")
    socket.create_connection = deny_tcp


def build_app(redis_dir: Path, worker_dir: Path):
    if not validate_scratch(redis_dir, worker_dir):
        raise ValueError("unsafe_celery_scratch")
    endpoint = str(redis_dir / "redis.sock")
    restrict_connections(endpoint)
    from celery import Celery
    url = f"redis+socket://{endpoint}?db=0"
    celery_app = Celery("flind_wave176_synthetic", broker=url, backend=url)
    celery_app.conf.update(
        task_default_queue=QUEUE, task_acks_late=True,
        task_track_started=True, task_serializer="json", result_serializer="json",
        accept_content=["json"], worker_prefetch_multiplier=1,
    )

    @celery_app.task(name="flind.wave176.synthetic.echo")
    def synthetic_echo(value: int):
        return {"synthetic": True, "value": value}

    @celery_app.task(bind=True, max_retries=1, name="flind.wave176.synthetic.retry")
    def synthetic_retry(self):
        if self.request.retries == 0:
            raise self.retry(countdown=0)
        return {"synthetic": True, "retries": self.request.retries}

    return celery_app


def qualify(redis_dir: Path, worker_dir: Path, *, timeout: int = 40) -> dict[str, object]:
    receipt: dict[str, object] = {
        "phase": "synthetic-isolated-celery-worker",
        "real_synthetic_worker_started": False,
        "synthetic_queue_roundtrip_qualified": False,
        "synthetic_retry_qualified": False,
        "result_backend_qualified": False,
        "first_party_worker_qualified": False,
        "tenant_auth_isolation_qualified": False,
        "ingestion_qualified": False,
        "release_qualified": False,
    }
    worker = None
    started = time.monotonic()
    try:
        if not 8 <= timeout <= 60 or not validate_scratch(redis_dir, worker_dir):
            raise ValueError("unsafe_celery_worker_admission")
        import redis
        client = redis.Redis(
            unix_socket_path=str(redis_dir / "redis.sock"),
            db=0, socket_timeout=3, socket_connect_timeout=3,
        )
        try:
            if not client.ping():
                raise ValueError("unavailable_synthetic_redis")
            cfg = client.config_get()
            if (int(cfg.get("port", -1)) != 0
                    or Path(cfg.get("dir", "")).resolve() != redis_dir.resolve()
                    or cfg.get("save") != "" or cfg.get("appendonly") != "no"
                    or not 0 < int(cfg.get("maxmemory", 0)) <= 64 * 1024 * 1024):
                raise ValueError("non_ephemeral_redis_not_allowed")
        finally:
            client.close()
        os.environ[ENV_REDIS] = str(redis_dir)
        os.environ[ENV_WORKER] = str(worker_dir)
        executor = build_app(redis_dir, worker_dir)
        project_root = Path(__file__).resolve().parents[2]
        environment = {key: value for key, value in os.environ.items() if key in (
            "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", ENV_REDIS, ENV_WORKER
        )}
        environment["PYTHONPATH"] = str(project_root)
        args = [
            sys.executable, "-m", "celery",
            "-A", "tools.flind.qualify_synthetic_celery_worker_wave176:app",
            "worker", "--pool=solo", "--concurrency=1",
            "--loglevel=INFO", "--queues=" + QUEUE,
            "--hostname=flind-wave176-synthetic@localhost",
            "--without-gossip", "--without-mingle", "--without-heartbeat",
        ]
        log_path = worker_dir / "synthetic-worker.log"
        with log_path.open("w", encoding="utf-8") as stream:
            worker = subprocess.Popen(
                args, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                cwd=project_root, env=environment, start_new_session=True,
            )
        deadline = time.monotonic() + min(timeout, 25)
        while time.monotonic() < deadline:
            if worker.poll() is not None:
                raise RuntimeError("synthetic_worker_exited_early")
            if "ready." in log_path.read_text(errors="replace"):
                receipt["real_synthetic_worker_started"] = True
                break
            time.sleep(0.2)
        if not receipt["real_synthetic_worker_started"]:
            raise RuntimeError("synthetic_worker_not_ready")
        a = executor.send_task(
            "flind.wave176.synthetic.echo", args=[73], queue=QUEUE,
        )
        b = executor.send_task("flind.wave176.synthetic.retry", queue=QUEUE)
        try:
            remaining = max(3, deadline + timeout - time.monotonic())
            v1 = a.get(timeout=min(remaining, timeout), propagate=True)
            v2 = b.get(timeout=min(remaining, timeout), propagate=True)
            receipt["synthetic_queue_roundtrip_qualified"] = (
                v1 == {"synthetic": True, "value": 73}
                and a.state == "SUCCESS"
            )
            receipt["synthetic_retry_qualified"] = (
                v2 == {"synthetic": True, "retries": 1}
                and b.state == "SUCCESS"
            )
            receipt["result_backend_qualified"] = (
                receipt["synthetic_queue_roundtrip_qualified"]
                and receipt["synthetic_retry_qualified"]
            )
            if not receipt["result_backend_qualified"]:
                raise RuntimeError("synthetic_worker_result_mismatch")
        finally:
            a.forget()
            b.forget()
    except Exception as exc:
        receipt["blocker"] = type(exc).__name__
    finally:
        if worker is not None:
            if worker.poll() is None:
                worker.send_signal(signal.SIGTERM)
            try:
                worker.wait(timeout=6)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=6)
            receipt["worker_stopped"] = worker.poll() is not None
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 1)
    return receipt


# Celery's -A module loader imports this module under a separate worker process.
# No app or network connection is created without the explicit scratch env vars.
app = build_app(Path(os.environ[ENV_REDIS]), Path(os.environ[ENV_WORKER])) if (
    ENV_REDIS in os.environ and ENV_WORKER in os.environ
) else None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--redis-dir", type=Path, required=True)
    p.add_argument("--worker-dir", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=40)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    result = qualify(args.redis_dir, args.worker_dir, timeout=args.timeout)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Flind isolated synthetic worker:", "PASS" if "blocker" not in result else "BLOCKED")
    return 0 if (
        "blocker" not in result and result["synthetic_queue_roundtrip_qualified"]
        and result["synthetic_retry_qualified"] and result.get("worker_stopped")
    ) else 2


if __name__ == "__main__":
    sys.exit(main())
