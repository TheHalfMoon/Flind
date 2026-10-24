#!/usr/bin/env python3
"""Check actual *local* service versions against Flind's settings contracts.

Read-only. Requirement specs are extracted as literals from source AST, so
Django/Celery settings and external integrations are never imported.
"""
from __future__ import annotations

import ast
import re
import socket
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__:
    from .qualify_ephemeral_clickhouse import sql_http
    from .qualify_ephemeral_redis import redis_command
else:
    from qualify_ephemeral_clickhouse import sql_http
    from qualify_ephemeral_redis import redis_command


REQUIREMENTS_FILE = Path(__file__).resolve().parents[2] / "posthog/settings/service_requirements.py"
SUPPORTED_SERVICES = ("postgresql", "redis", "clickhouse")
VERSION_PATTERN = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.\d+)?(?:\b|[- (])")
SPEC_PATTERN = re.compile(r"^(>=|<=|==|>|<)(\d+(?:\.\d+){0,2})$")


@dataclass(frozen=True)
class VersionCheck:
    service: str
    version: str | None
    requirement: str
    supported: bool
    evidence: str


def parse_version(value: str) -> tuple[int, int, int]:
    match = VERSION_PATTERN.match(value.strip())
    if not match:
        raise ValueError("Unrecognized service version")
    return tuple(int(part or 0) for part in match.groups())


def version_matches_spec(version: str, spec: str) -> bool:
    actual = parse_version(version)
    if not spec or not all(
        SPEC_PATTERN.fullmatch(item.strip()) for item in spec.split(",")
    ):
        raise ValueError("Unsupported version-spec syntax")
    for clause in spec.split(","):
        match = SPEC_PATTERN.fullmatch(clause.strip())
        assert match is not None
        op, value = match.groups()
        bound = parse_version(value)
        # semantic_version.SimpleSpec in Flind treats partial requirements
        # (e.g. <=25.12) as an inclusive entire minor line, not <=25.12.0.
        component_count = len(value.split("."))
        lhs, rhs = actual[:component_count], bound[:component_count]
        passed = {
            ">=": lhs >= rhs,
            ">": lhs > rhs,
            "<=": lhs <= rhs,
            "<": lhs < rhs,
            "==": lhs == rhs,
        }[op]
        if not passed:
            return False
    return True


def source_requirements(path: Path = REQUIREMENTS_FILE) -> dict[str, str]:
    """Static extraction fails closed if source requirements are changed."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "ServiceVersionRequirement":
            continue
        kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords}
        service, spec = kwargs.get("service"), kwargs.get("supported_version")
        if (
            service not in SUPPORTED_SERVICES
            or service in found
            or not isinstance(spec, str)
        ):
            raise ValueError("Unexpected/duplicate service requirement")
        # Syntax check even before attempting a network check.
        version_matches_spec("1.0.0", spec)
        found[service] = spec
    if set(found) != set(SUPPORTED_SERVICES):
        raise ValueError("Incomplete Flind service requirements")
    return found


def postgres_version() -> str:
    process = subprocess.run(
        ["psql", "-X", "-h", "127.0.0.1", "-p", "5432", "-d", "postgres",
         "-A", "-t", "-c", "SHOW server_version"],
        capture_output=True, text=True, check=False, timeout=4,
    )
    if process.returncode != 0 or not process.stdout.strip():
        raise ValueError("PostgreSQL read-only version query unavailable")
    return process.stdout.strip()


def redis_version(port: int) -> str:
    with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
        conn.settimeout(2)
        with conn.makefile("rwb") as stream:
            payload = redis_command(stream, b"INFO", b"server", max_bulk_bytes=16384)
    if not isinstance(payload, bytes):
        raise ValueError("Redis INFO server unavailable")
    for line in payload.decode("ascii", errors="replace").splitlines():
        if line.startswith("redis_version:"):
            return line.removeprefix("redis_version:").strip()
    raise ValueError("Redis version unavailable")


def clickhouse_version(port: int) -> str:
    return sql_http(port, "SELECT version()").decode("ascii").strip()


def qualify_service_versions(
    redis_port: int,
    clickhouse_port: int,
    requirement_file: Path = REQUIREMENTS_FILE,
) -> dict:
    try:
        specs = source_requirements(requirement_file)
    except (OSError, SyntaxError, TypeError, ValueError):
        return {
            "version_requirements_met": False,
            "release_qualified": False,
            "blocked_by": list(SUPPORTED_SERVICES),
            "checks": [],
            "reason": "Unable to verify service version requirements",
        }
    checks: list[VersionCheck] = []
    resolvers = {
        "postgresql": postgres_version,
        "redis": lambda: redis_version(redis_port),
        "clickhouse": lambda: clickhouse_version(clickhouse_port),
    }
    for service in SUPPORTED_SERVICES:
        try:
            version = resolvers[service]()
            supported = version_matches_spec(version, specs[service])
            evidence = "supported" if supported else "outside required range"
        except (OSError, ValueError, subprocess.TimeoutExpired, UnicodeError):
            version, supported, evidence = None, False, "version check unavailable"
        checks.append(VersionCheck(service, version, specs[service], supported, evidence))
    blockers = [entry.service for entry in checks if not entry.supported]
    return {
        "version_requirements_met": not blockers,
        "release_qualified": False,
        "blocked_by": blockers,
        "checks": [asdict(item) for item in checks],
    }
