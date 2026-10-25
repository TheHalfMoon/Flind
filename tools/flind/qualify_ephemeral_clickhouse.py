#!/usr/bin/env python3
"""Start only a loopback, memory-bounded temporary ClickHouse HTTP server.

Real CREATE/INSERT/SELECT/DROP occurs inside a private temporary directory.
Never configures system services, touches an existing database or claims E2E.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
from http.client import HTTPConnection, HTTPException
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from xml.sax.saxutils import escape

if __package__:
    from .qualify_backend_runtime import clickhouse_ping, qualify
else:
    from qualify_backend_runtime import clickhouse_ping, qualify


def pick_loopback_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def write_isolated_config(root: Path, port: int) -> Path:
    for name in ("data", "tmp", "user_files", "format_schemas", "logs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    users = root / "users.xml"
    users.write_text(
        "<clickhouse>"
        "<profiles><default><max_memory_usage>134217728</max_memory_usage>"
        "</default></profiles>"
        "<users><default><password></password>"
        "<networks><ip>127.0.0.1</ip></networks>"
        "<profile>default</profile><quota>default</quota>"
        "</default></users><quotas><default/></quotas></clickhouse>",
        encoding="utf-8",
    )
    conf = root / "config.xml"
    path = lambda name: escape(str(root / name))
    conf.write_text(
        "<clickhouse>"
        "<logger><level>warning</level><console>1</console></logger>"
        "<listen_host>127.0.0.1</listen_host>"
        f"<http_port>{port}</http_port><tcp_port>0</tcp_port>"
        f"<path>{path('data')}/</path>"
        f"<tmp_path>{path('tmp')}/</tmp_path>"
        f"<user_files_path>{path('user_files')}/</user_files_path>"
        f"<format_schema_path>{path('format_schemas')}/</format_schema_path>"
        f"<users_config>{escape(str(users))}</users_config>"
        "<max_server_memory_usage>536870912</max_server_memory_usage>"
        "<max_server_memory_usage_to_ram_ratio>0.1</max_server_memory_usage_to_ram_ratio>"
        "<background_pool_size>16</background_pool_size>"
        "<background_schedule_pool_size>2</background_schedule_pool_size>"
        "</clickhouse>",
        encoding="utf-8",
    )
    return conf


def sql_http(port: int, query: str) -> bytes:
    """Never redirect: POST only to loopback with bounded response body."""
    if len(query) > 256:
        raise ValueError("Oversize test query")
    client = HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        client.request("POST", "/", body=query.encode("ascii"),
                       headers={"Content-Type": "text/plain"})
        response = client.getresponse()
        content = response.read(1024)
        if response.status != 200:
            raise ValueError("ClickHouse test SQL refused")
        return content
    finally:
        client.close()


def query_roundtrip(port: int) -> dict:
    if sql_http(port, "SELECT 1").strip() != b"1":
        raise ValueError("ClickHouse SELECT 1 mismatch")
    sql_http(port, "CREATE TABLE flind_probe (id UInt32) ENGINE = Memory")
    try:
        sql_http(port, "INSERT INTO flind_probe VALUES (10),(20),(30)")
        received = sql_http(port, "SELECT count(),sum(id) FROM flind_probe").strip()
        if received != b"3\t60":
            raise ValueError("ClickHouse read-back mismatch")
        return {"rows": 3, "sum": 60}
    finally:
        sql_http(port, "DROP TABLE IF EXISTS flind_probe")


def local_service_versions(redis_port: int, clickhouse_port: int) -> dict:
    if __package__:
        from .qualify_service_versions import qualify_service_versions
    else:
        from qualify_service_versions import qualify_service_versions
    return qualify_service_versions(redis_port, clickhouse_port)


def isolated_clickhouse(
    binary: str | None = None,
    redis_port: int = 6379,
    on_ready: Callable[[int], dict] | None = None,
) -> dict:
    executable = binary or shutil.which("clickhouse")
    if not executable:
        return {
            "isolated_clickhouse_passed": False,
            "release_qualified": False,
            "reason": "ClickHouse binary unavailable",
        }
    with tempfile.TemporaryDirectory(prefix="flind-clickhouse-") as temp:
        root = Path(temp)
        port = pick_loopback_port()
        config = write_isolated_config(root, port)
        with (root / "logs" / "output").open("wb") as output:
            try:
                child = subprocess.Popen(
                    [executable, "server", f"--config-file={config}"],
                    cwd=root, stdout=output, stderr=output,
                )
            except OSError:
                return {
                    "isolated_clickhouse_passed": False,
                    "release_qualified": False,
                    "reason": "ClickHouse process could not start",
                }
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        raise RuntimeError("ClickHouse exited before readiness")
                    if clickhouse_ping(port).ready:
                        observed = query_roundtrip(port)
                        # Follow-on probes share only this private, temporary
                        # loopback server. Any failure fails qualification;
                        # never return a successful component receipt.
                        child_probe = on_ready(port) if on_ready else None
                        return {
                            "isolated_clickhouse_passed": True,
                            **({"event_readback": child_probe} if child_probe is not None else {}),
                            "release_qualified": False,
                            "http_query_roundtrip": observed,
                            "storage": "temporary Memory engine only",
                            "network": "127.0.0.1 only",
                            "memory_limit_bytes": 536870912,
                            "backend_prerequisites": qualify(
                                redis_port=redis_port, clickhouse_port=port,
                            ),
                            "service_versions": local_service_versions(
                                redis_port, port,
                            ),
                        }
                    time.sleep(0.2)
                raise RuntimeError("ClickHouse startup exceeded 30 seconds")
            except (OSError, RuntimeError, ValueError, HTTPException) as exc:
                return {
                    "isolated_clickhouse_passed": False,
                    "release_qualified": False,
                    "reason": str(exc),
                }
            finally:
                child.terminate()
                try:
                    child.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=4)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = isolated_clickhouse()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind isolated ClickHouse: " +
              ("PASS" if result["isolated_clickhouse_passed"] else "BLOCKED"))
        print("Flind release E2E: NOT QUALIFIED")
    return 0 if result["isolated_clickhouse_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
