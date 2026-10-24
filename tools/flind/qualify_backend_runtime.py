#!/usr/bin/env python3
"""Read-only local service preflight, NOT end-to-end Flind release qualification.

Never creates databases, writes data, starts containers, installs dependencies,
contacts external networks, or prints usernames, credentials or environment data.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import socket
from http.client import HTTPConnection, HTTPException
from pathlib import Path
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Check:
    name: str
    ready: bool
    evidence: str
    required: bool = True


def postgres_readonly_sql() -> Check:
    if not shutil.which("psql"):
        return Check("postgres", False, "PostgreSQL CLI unavailable")
    try:
        proc = subprocess.run(
            ["psql", "-X", "-h", "127.0.0.1", "-p", "5432",
             "-d", "postgres", "-A", "-t", "-c", "SELECT 1"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip() == "1":
            return Check("postgres", True, "Read-only SELECT 1 succeeded")
        return Check("postgres", False, "Read-only SQL not available")
    except (OSError, subprocess.TimeoutExpired):
        return Check("postgres", False, "Read-only SQL not available")


def pinned_python_version(
    version: tuple[int, int, int] | None = None,
    project_root: Path | None = None,
) -> Check:
    """Require the exact Python patch pinned by Flind, not merely Django import."""
    root = project_root or Path(__file__).resolve().parents[2]
    try:
        with (root / "pyproject.toml").open("rb") as f:
            spec = tomllib.load(f)["project"]["requires-python"]
        if not isinstance(spec, str) or not spec.startswith("=="):
            return Check("python", False, "Exact Python requirement unavailable")
        expected = tuple(int(piece) for piece in spec[2:].split("."))
        if len(expected) != 3:
            return Check("python", False, "Exact Python requirement unavailable")
    except (OSError, KeyError, TypeError, ValueError):
        return Check("python", False, "Exact Python requirement unavailable")
    active = version or tuple(sys.version_info[:3])
    correct = active == expected
    return Check(
        "python",
        correct,
        f"Python {'.'.join(map(str, active))}: "
        + ("matches" if correct else "does not match")
        + f" pinned {'.'.join(map(str, expected))}",
    )


def redis_ping(port: int = 6379) -> Check:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5) as conn:
            conn.settimeout(1.5)
            conn.sendall(b"*1\r\n$4\r\nPING\r\n")
            response = conn.recv(64)
        return Check("redis", response.startswith(b"+PONG"), "Local PING succeeded"
                     if response.startswith(b"+PONG") else "Local PING unavailable")
    except OSError:
        return Check("redis", False, "Local PING unavailable")


def clickhouse_ping(port: int = 8123) -> Check:
    # HTTPConnection never follows a 3xx redirect out of the loopback host.
    conn = HTTPConnection("127.0.0.1", port, timeout=1.5)
    try:
        conn.request("GET", "/ping")
        response = conn.getresponse()
        ok = response.status == 200 and response.read(64).strip().lower() == b"ok."
        return Check("clickhouse", ok, "Local HTTP ping succeeded"
                     if ok else "Local HTTP ping unavailable")
    except (OSError, HTTPException, ValueError):
        return Check("clickhouse", False, "Local HTTP ping unavailable")
    finally:
        conn.close()


def django_import() -> Check:
    ok = importlib.util.find_spec("django") is not None
    return Check("django", ok, "Django installed in current Python environment"
                 if ok else "Django missing from current Python environment")


def docker_daemon() -> Check:
    if not shutil.which("docker"):
        return Check("docker", False, "Docker CLI unavailable", required=False)
    local_socket = Path.home() / ".docker" / "run" / "docker.sock"
    if not local_socket.exists():
        local_socket = Path("/var/run/docker.sock")
    if not local_socket.exists():
        return Check("docker", False, "Local Docker socket unavailable", required=False)
    try:
        # Force a Unix socket, ignoring any remotely configured Docker context.
        proc = subprocess.run(
            ["docker", "--host", "unix://" + str(local_socket),
             "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=4, check=False,
        )
        ok = proc.returncode == 0 and bool(proc.stdout.strip())
        return Check("docker", ok, "Local Docker daemon reachable"
                     if ok else "Local Docker daemon unavailable", required=False)
    except (OSError, subprocess.TimeoutExpired):
        return Check("docker", False, "Local Docker daemon unavailable", required=False)


def qualify(redis_port: int = 6379, clickhouse_port: int = 8123) -> dict:
    checks = [
        pinned_python_version(), postgres_readonly_sql(), redis_ping(redis_port),
        clickhouse_ping(clickhouse_port), django_import(), docker_daemon(),
    ]
    blockers = [c.name for c in checks if c.required and not c.ready]
    return {
        "phase": "local-backend-prerequisites",
        "prerequisites_ready": not blockers,
        "release_qualified": False,
        "blocked_by": blockers,
        "checks": [asdict(c) for c in checks],
        "qualification_note": (
            "Even a fully ready local service preflight is not Django/DB/SDK "
            "ingestion, auth, migration, API, browser or release E2E evidence"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable result")
    parser.add_argument(
        "--redis-port", type=int, default=6379,
        help="Loopback-only Redis port for isolated local test instances",
    )
    parser.add_argument(
        "--clickhouse-port", type=int, default=8123,
        help="Loopback-only ClickHouse HTTP port for isolated local instances",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.redis_port <= 65535:
        parser.error("--redis-port must be between 1 and 65535")
    if not 1 <= args.clickhouse_port <= 65535:
        parser.error("--clickhouse-port must be between 1 and 65535")
    result = qualify(args.redis_port, args.clickhouse_port)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Flind local backend prerequisites:",
              "READY" if result["prerequisites_ready"] else "BLOCKED")
        for check in result["checks"]:
            label = ("READY" if check["ready"] else
                     "BLOCKED" if check["required"] else "OPTIONAL/UNAVAILABLE")
            print("  " + check["name"] + ": " + label +
                  " (" + check["evidence"] + ")")
        print("Release E2E: NOT QUALIFIED")
    return 0 if result["prerequisites_ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
