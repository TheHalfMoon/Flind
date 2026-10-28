#!/usr/bin/env python3
"""Read-only Flind Wave216 service readiness; never trust a port alone."""
import base64
import json
import uuid
import subprocess
import sys
import urllib.request

PROJECT = "flindwave216"
SERVICES = {"postgres": 15439, "redis": 16380, "clickhouse": 18124}


def require(condition, message):
    """Fail closed even when Python runs with -O (asserts disabled)."""
    if not condition:
        raise AssertionError(message)

def inspect(service):
    name = f"{PROJECT}-{service}-1"
    run = subprocess.run(
        ["docker", "inspect", name], text=True, capture_output=True, timeout=15, check=True
    )
    return json.loads(run.stdout)[0]

def assert_owned_service(service, data):
    labels = data["Config"]["Labels"]
    require(labels.get("com.docker.compose.project") == PROJECT, "wrong Compose project")
    require(labels.get("com.docker.compose.service") == service, "wrong service label")
    require(data["State"]["Running"], "isolated Flind service is not running")
    require(data["State"].get("Health", {}).get("Status") == "healthy", "unhealthy test service")
    ports = data["NetworkSettings"]["Ports"]
    target_port = {"postgres": "5432/tcp", "redis": "6379/tcp", "clickhouse": "8123/tcp"}[service]
    publishes = ports.get(target_port) or []
    require(len(publishes) == 1, "unexpected port mappings")
    p = publishes[0]
    require(p["HostIp"] == "127.0.0.1", "service exposed beyond loopback")
    require(int(p["HostPort"]) == SERVICES[service], "unexpected host port")

def clickhouse_sql(query):
    auth = base64.b64encode(b"flind_test:flind_local_only").decode("ascii")
    request = urllib.request.Request(
        "http://127.0.0.1:18124/?database=flind_test_wave216abc123",
        data=query.encode("utf-8"), method="POST",
        headers={"Authorization": "Basic " + auth}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8").strip()

def check_synthetic_clickhouse_write():
    # Only after ownership verification; table name is unique within the
    # disposable flindwave216 ClickHouse database. No app tables touched.
    table = "flind_w216_probe_" + uuid.uuid4().hex[:12]
    clickhouse_sql(f"CREATE TABLE {table} (team_id UInt32, event String) ENGINE=MergeTree ORDER BY (team_id,event)")
    try:
        clickhouse_sql(f"INSERT INTO {table} VALUES (101, 'synthetic-a'), (202, 'synthetic-b')")
        require(
            clickhouse_sql(f"SELECT count() FROM {table} WHERE team_id=101") == "1",
            "synthetic tenant 101 not isolated",
        )
        require(
            clickhouse_sql(f"SELECT count() FROM {table} WHERE team_id=202") == "1",
            "synthetic tenant 202 not isolated",
        )
        require(clickhouse_sql(f"SELECT count() FROM {table}") == "2", "synthetic ClickHouse row count mismatch")
        return True
    finally:
        clickhouse_sql(f"DROP TABLE {table}")

def read_database_names():
    r = subprocess.run(
        ["docker", "exec", f"{PROJECT}-postgres-1", "psql", "-U", "flind_test",
         "-d", "test_posthog", "-tAc",
         "SELECT datname FROM pg_database WHERE datname LIKE 'test_%' ORDER BY datname"],
        text=True, capture_output=True, timeout=20, check=True
    )
    actual = set(r.stdout.splitlines())
    expected = {"test_posthog", "test_persons", "test_behavioral_cohorts", "test_cyclotron_node"}
    require(expected <= actual, "isolated PG test databases missing")
    return sorted(expected)

def check_redis():
    r = subprocess.run(
        ["docker", "exec", f"{PROJECT}-redis-1", "redis-cli", "PING"],
        text=True, capture_output=True, timeout=15, check=True
    )
    require(r.stdout.strip() == "PONG", "isolated Redis unavailable")

def check_clickhouse():
    database = "flind_test_wave216abc123"
    auth = base64.b64encode(b"flind_test:flind_local_only").decode("ascii")
    request = urllib.request.Request(
        "http://127.0.0.1:18124/?database=" + database + "&query=SELECT%20currentDatabase()",
        headers={"Authorization": "Basic " + auth}
    )
    with urllib.request.urlopen(request, timeout=15) as r:
        require(r.read().decode().strip() == database, "wrong ClickHouse database")
    return database

if __name__ == "__main__":
    try:
        for name in SERVICES:
            assert_owned_service(name, inspect(name))
        databases = read_database_names()
        check_redis()
        clickhouse_db = check_clickhouse()
        write_probe = "--synthetic-clickhouse-write-probe" in sys.argv
        if write_probe:
            require(len(sys.argv) == 2, "unknown arguments")
            check_synthetic_clickhouse_write()
        else:
            require(len(sys.argv) == 1, "unknown arguments")
        print(json.dumps({
            "status": "PASS",
            "scope": "isolated_databases_only_not_joined_ingestion",
            "compose_project": PROJECT,
            "loopback_only": True,
            "postgres_databases": databases,
            "redis_ping": "PONG",
            "clickhouse_database": clickhouse_db,
            "synthetic_clickhouse_read_write": write_probe,
            "release_qualified": False
        }, sort_keys=True))
    except Exception as exc:
        print("FLIND_WAVE216_FAIL " + str(exc), file=sys.stderr)
        raise SystemExit(1)
