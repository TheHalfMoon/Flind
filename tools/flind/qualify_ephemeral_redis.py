#!/usr/bin/env python3
"""Exercise a private no-persistence Redis instance; terminate it in finally.

No existing Redis instance, data, daemon, user service, container or remote
network is touched. This is a Redis component check, never release E2E.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
import json
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __package__:
    from .qualify_backend_runtime import redis_ping, qualify
else:
    from qualify_backend_runtime import redis_ping, qualify


def redis_command(stream, *pieces: bytes) -> bytes | int | None:
    """Send one RESP2 command and read a bounded response."""
    if not all(isinstance(p, bytes) and len(p) <= 512 for p in pieces):
        raise ValueError("Command exceeds bounded test payload")
    packet = b"*" + str(len(pieces)).encode() + b"\r\n"
    packet += b"".join(
        b"$" + str(len(piece)).encode() + b"\r\n" + piece + b"\r\n"
        for piece in pieces
    )
    stream.write(packet)
    stream.flush()
    line = stream.readline(1024)
    if not line.endswith(b"\r\n"):
        raise ValueError("Invalid Redis response")
    kind, value = line[:1], line[1:-2]
    if kind == b"+":
        return value
    if kind == b":":
        return int(value)
    if kind == b"-":
        raise ValueError("Redis command returned an error")
    if kind == b"$":
        count = int(value)
        if count == -1:
            return None
        if count > 1024 or count < 0:
            raise ValueError("Oversize or invalid Redis bulk response")
        payload = stream.read(count + 2)
        if len(payload) != count + 2 or not payload.endswith(b"\r\n"):
            raise ValueError("Invalid Redis bulk response")
        return payload[:-2]
    raise ValueError("Unexpected Redis response")


def pick_loopback_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def redis_command_check(port: int) -> None:
    """Write ONLY to the process-private temporary Redis instance."""
    with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
        conn.settimeout(2)
        stream = conn.makefile("rwb")
        try:
            key = ("flind-ephemeral-" + secrets.token_hex(12)).encode()
            value = secrets.token_bytes(24)
            if redis_command(stream, b"PING") != b"PONG":
                raise ValueError("PING refused")
            if redis_command(stream, b"SET", key, value) != b"OK":
                raise ValueError("SET failed")
            if redis_command(stream, b"GET", key) != value:
                raise ValueError("GET mismatch")
            if redis_command(stream, b"DEL", key) != 1:
                raise ValueError("DEL failed")
            if redis_command(stream, b"GET", key) is not None:
                raise ValueError("Deleted key returned data")
        finally:
            stream.close()


def isolated_redis(
    binary: str | None = None,
    on_ready: Callable[[int], dict] | None = None,
) -> dict:
    resolved = binary or shutil.which("redis-server")
    if not resolved:
        return {
            "isolated_redis_passed": False,
            "release_qualified": False,
            "reason": "Redis binary unavailable",
        }
    with tempfile.TemporaryDirectory(prefix="flind-redis-") as temporary:
        port = pick_loopback_port()
        # No login daemon, persistence, remote bind, cross-project keys, or paid runtime.
        cmd = [
            resolved, "--bind", "127.0.0.1", "--port", str(port),
            "--protected-mode", "yes",
            "--save", "", "--appendonly", "no",
            "--daemonize", "no", "--maxmemory", "64mb",
            "--maxmemory-policy", "noeviction",
            "--dir", temporary, "--loglevel", "warning",
        ]
        child = subprocess.Popen(
            cmd, cwd=temporary, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise RuntimeError("Isolated Redis exited before readiness")
                if redis_ping(port).ready:
                    redis_command_check(port)
                    nested = on_ready(port) if on_ready else None
                    return {
                        "isolated_redis_passed": True,
                        "release_qualified": False,
                        "tests": ["PING", "SET", "GET", "DEL", "GET-after-delete"],
                        "persistence": "disabled",
                        "network": "127.0.0.1 only",
                        "backend_prerequisites": qualify(redis_port=port),
                        **({"nested_clickhouse": nested} if nested is not None else {}),
                    }
                time.sleep(0.1)
            raise RuntimeError("Isolated Redis did not become ready")
        except (OSError, RuntimeError, ValueError) as exc:
            return {
                "isolated_redis_passed": False,
                "release_qualified": False,
                "reason": str(exc),
            }
        finally:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = isolated_redis()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind isolated Redis: " +
              ("PASS" if result["isolated_redis_passed"] else "BLOCKED"))
        print("Flind release E2E: NOT QUALIFIED")
    return 0 if result["isolated_redis_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
