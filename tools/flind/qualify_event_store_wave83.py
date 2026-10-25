#!/usr/bin/env python3
"""Real synthetic Flind event-column readback in disposable localhost ClickHouse.

This is a component qualification, NOT SDK capture, Kafka or dashboard E2E.
No shared database, paid service, real event/person data or network egress.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from uuid import UUID

if __package__:
    from .qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http
else:
    from qualify_ephemeral_clickhouse import isolated_clickhouse, sql_http


ROOT = Path(__file__).resolve().parents[2]
TABLE = "flind_wave83_events"
# Exact canonical field names and types sourced from EVENTS_TABLE_BASE_SQL;
# the test table intentionally omits the dozens of additional production
# fields and uses Memory rather than replicated/distributed production DDL.
CANONICAL_FIELDS = (
    ("uuid", "UUID"),
    ("event", "VARCHAR"),
    ("properties", "VARCHAR"),
    ("timestamp", "DateTime64(6, 'UTC')"),
    ("team_id", "Int64"),
    ("distinct_id", "VARCHAR"),
)

CREATE_SQL = (
    "CREATE TABLE flind_wave83_events "
    "(uuid UUID,event String,properties String,"
    "timestamp DateTime64(6,'UTC'),team_id Int64,distinct_id String) "
    "ENGINE=Memory"
)

# Deliberately synthetic IDs, users, events and paths; nothing user-specific.
EVENTS = (
    (101, "user-one", "$pageview", "/home"),
    (101, "user-two", "$pageview", "/pricing"),
    (101, "user-one", "$pageleave", "/home"),
    (101, "user-one", "purchase", "/pricing"),
    (202, "user-one", "$pageview", "/private"),
    (202, "user-three", "$pageview", "/elsewhere"),
)


def original_event_columns_present(root: Path = ROOT) -> bool:
    """Require every claimed field to exist in the actual event SQL template."""
    source = (root / "posthog/models/event/sql.py").read_text(encoding="utf-8")
    marker = 'EVENTS_TABLE_BASE_SQL = """'
    if source.count(marker) != 1:
        return False
    template = source.split(marker, 1)[1].split('"""', 1)[0]
    for field, dtype in CANONICAL_FIELDS:
        pattern = rf"(?m)^[ \t]*{re.escape(field)}[ \t]+{re.escape(dtype)}(?:[ \t]+[^\r\n,]*)?[ \t]*,"
        if not re.search(pattern, template):
            return False
    return True


def team_scoped_summary_sql(team_id: int) -> str:
    """Only an exact positive 64-bit team ID is accepted, never SQL fragments."""
    if type(team_id) is not int or not 1 <= team_id <= 2**63 - 1:
        raise ValueError("Invalid positive 64-bit event team ID")
    return (
        "SELECT count(),countIf(event='$pageview'),"
        "uniqExactIf(distinct_id,event='$pageview'),"
        "countIf(event='purchase') "
        f"FROM {TABLE} WHERE team_id={team_id}"
    )


def synthetic_insert_sql(index: int) -> str:
    if type(index) is not int or not 0 <= index < len(EVENTS):
        raise ValueError("Invalid synthetic fixture index")
    team, distinct, event, path = EVENTS[index]
    if not (
        type(team) is int
        and 1 <= team <= 2**63 - 1
        and re.fullmatch(r"[a-z][a-z-]{0,30}", distinct)
        and re.fullmatch(r"\$?[a-z][a-z_]{0,30}", event)
        and re.fullmatch(r"/[a-z]{1,40}", path)
    ):
        raise ValueError("Synthetic event fixture invalid")
    event_id = str(UUID(int=index + 1))
    props = json.dumps({"$pathname": path}, separators=(",", ":"), ensure_ascii=True)
    sql = (
        f"INSERT INTO {TABLE} (uuid,event,properties,timestamp,team_id,distinct_id) "
        f"VALUES ('{event_id}','{event}','{props}',"
        f"'2026-10-25 00:00:00',{team},'{distinct}')"
    )
    if len(sql) > 256 or not sql.isascii():
        raise ValueError("Synthetic event exceeds the isolated HTTP SQL bound")
    return sql


def event_roundtrip(port: int) -> dict:
    if not original_event_columns_present():
        raise ValueError("Canonical Flind event schema fields changed")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid isolated ClickHouse port")
    # Memory engine is temporary; server's database and process are also
    # private, temporary, and destroyed by isolated_clickhouse().
    sql_http(port, CREATE_SQL)
    try:
        for i in range(len(EVENTS)):
            sql_http(port, synthetic_insert_sql(i))

        a = sql_http(port, team_scoped_summary_sql(101)).strip()
        b = sql_http(port, team_scoped_summary_sql(202)).strip()
        if a != b"4\t2\t2\t1" or b != b"2\t2\t2\t0":
            raise ValueError("Synthetic team-scoped event aggregate mismatch")

        # A colliding distinct_id ('user-one') exists on both teams. Team
        # filters must also exclude a page path belonging only to the other.
        private_from_a = sql_http(
            port,
            f"SELECT count() FROM {TABLE} WHERE team_id=101 AND properties LIKE '%/private%'"
        ).strip()
        pricing_from_b = sql_http(
            port,
            f"SELECT count() FROM {TABLE} WHERE team_id=202 AND properties LIKE '%/pricing%'"
        ).strip()
        if private_from_a != b"0" or pricing_from_b != b"0":
            raise ValueError("Team-filtered event data leaked another team's path")

        return {
            "canonical_flind_event_fields_matched": True,
            "real_clickhouse_insert_select_passed": True,
            "synthetic_events_inserted": len(EVENTS),
            "distinct_teams": 2,
            "team_101": {"rows": 4, "pageviews": 2, "unique_pageview_ids": 2, "purchases": 1},
            "team_202": {"rows": 2, "pageviews": 2, "unique_pageview_ids": 2, "purchases": 0},
            "colliding_distinct_ids_scoped": True,
            "cross_team_path_readback_absent": True,
            "engine": "temporary ClickHouse Memory",
            "sdk_ingestion_qualified": False,
            "kafka_ingestion_qualified": False,
            "dashboard_query_qualified": False,
            "release_qualified": False,
        }
    finally:
        sql_http(port, f"DROP TABLE IF EXISTS {TABLE}")


def qualify_event_store() -> dict:
    result = isolated_clickhouse(on_ready=event_roundtrip)
    tested = result.get("event_readback") or {}
    qualified = (
        result.get("isolated_clickhouse_passed") is True
        and tested.get("real_clickhouse_insert_select_passed") is True
        and tested.get("canonical_flind_event_fields_matched") is True
        and tested.get("cross_team_path_readback_absent") is True
    )
    return {
        "isolated_clickhouse_passed": result.get("isolated_clickhouse_passed") is True,
        "real_flind_shaped_event_readback_qualified": qualified,
        "synthetic_event_receipt": tested if qualified else {},
        "temporary_database": True,
        "sdk_ingestion_qualified": False,
        "kafka_ingestion_qualified": False,
        "dashboard_query_qualified": False,
        "release_qualified": False,
        **({"blocker": result.get("reason") or "Real ClickHouse readback unqualified"} if not qualified else {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = qualify_event_store()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Real isolated Flind-shaped event readback:", "PASS" if result["real_flind_shaped_event_readback_qualified"] else "BLOCKED")
        print("SDK/Kafka/dashboard E2E: NOT QUALIFIED")
    return 0 if result["real_flind_shaped_event_readback_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
