import base64
from pathlib import Path
from types import SimpleNamespace

from django.core.management.base import CommandError

import pytest
from unittest.mock import patch

import responses
from infi.clickhouse_orm import Database
from requests import PreparedRequest

from posthog.clickhouse.client import connection
from posthog.clickhouse.client.connection import ClickHouseCredentials, ClickHouseUser
from posthog.management.commands.migrate_clickhouse import Command

CLICKHOUSE_URL = "http://clickhouse.example.com:8123/"
APPLY_OPTIONS = {"upto": 99_999, "fake": False, "check": False, "plan": False, "print_sql": False}
SERVER_ANSWERS = {
    "SELECT count() FROM system.databases": "1",
    "SELECT version()": "25.8.1.1",
    "SELECT timezone()": "UTC",
}


def basic_auth(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


@pytest.mark.parametrize(
    "migrations_user_registered, first_request_auth, request_after_rotation_auth",
    [
        pytest.param(
            True,
            basic_auth("migrations", "token-1"),
            basic_auth("migrations", "token-2"),
            id="migrations_user_reads_its_token_per_request",
        ),
        pytest.param(
            False,
            basic_auth("default", "default-static"),
            basic_auth("default", "default-static"),
            id="unset_migrations_user_falls_back_to_default",
        ),
    ],
)
def test_migrate_authenticates_each_request_with_the_current_password(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    migrations_user_registered: bool,
    first_request_auth: str,
    request_after_rotation_auth: str,
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("token-1")
    users = {ClickHouseUser.DEFAULT: ClickHouseCredentials(user="default", password="default-static")}
    if migrations_user_registered:
        users[ClickHouseUser.MIGRATIONS] = ClickHouseCredentials(
            user="migrations", password="", password_file=str(token_file)
        )
    monkeypatch.setattr(connection, "__user_dict", users)
    sent_auth: list[str] = []

    def answer(request: PreparedRequest) -> tuple[int, dict[str, str], str]:
        sent_auth.append(str(request.headers["Authorization"]))
        body = request.body.decode() if isinstance(request.body, bytes) else str(request.body)
        return 200, {}, next((text for query, text in SERVER_ANSWERS.items() if body.startswith(query)), "")

    def apply_past_a_token_rotation(database: Database, *args: object, **kwargs: object) -> None:
        token_file.write_text("token-2")
        database._send("SELECT 1")

    with (
        responses.RequestsMock() as server,
        patch.object(Database, "migrate", autospec=True, side_effect=apply_past_a_token_rotation),
        patch("posthog.management.commands.migrate_clickhouse.default_client"),
    ):
        server.add_callback(responses.POST, CLICKHOUSE_URL, callback=answer)
        Command().migrate(CLICKHOUSE_URL, APPLY_OPTIONS)

    assert sent_auth[0] == first_request_auth
    assert sent_auth[-1] == request_after_rotation_auth

@pytest.mark.parametrize("inspection_option", ["plan", "check"])
def test_inspection_never_precreates_database_or_tracking_tables(inspection_option: str) -> None:
    """Planning and checking must never mutate even the migration metadata."""
    synthetic_creds = ClickHouseCredentials(user="migrations", password="owner-fixture")
    with (
        patch(
            "posthog.management.commands.migrate_clickhouse.get_clickhouse_creds",
            return_value=synthetic_creds,
        ),
        patch("posthog.management.commands.migrate_clickhouse.Database") as database_constructor,
        patch.object(Command, "_create_database_if_not_exists") as create_database,
        patch.object(Command, "_create_migration_tracking_tables_if_not_exist") as create_tracking,
        patch.object(Command, "get_migrations", return_value=[]),
        patch.object(Command, "get_applied_migrations", return_value=set()),
    ):
        Command().migrate(CLICKHOUSE_URL, {**APPLY_OPTIONS, inspection_option: True})
    create_database.assert_not_called()
    create_tracking.assert_not_called()
    database_constructor.assert_called_once()
    assert database_constructor.call_args.kwargs["readonly"] is True
    assert database_constructor.call_args.kwargs["autocreate"] is False
    assert database_constructor.call_args.kwargs["trust_env"] is False
    database_constructor.return_value.migrate.assert_not_called()
    database_constructor.return_value.insert.assert_not_called()


@pytest.mark.parametrize(
    "upto, already_applied, expected",
    [
        (0, (), []),
        (3, (), ["0001_initial"]),
        (4, (), ["0001_initial", "0004_patch"]),
        (5, (), ["0001_initial", "0004_patch"]),
        (4, ("0001_initial", "0004_patch"), []),
        (4, ("0001_initial",), ["0004_patch"]),
    ],
)
def test_migration_selection_respects_upto_before_yield(
    upto: int, already_applied: tuple[str, ...], expected: list[str]
) -> None:
    # Original product Command method; gap between migration 0004 and 0007
    # previously let --plan and --fake include the out-of-range migration.
    modules = {
        name: SimpleNamespace(operations=[])
        for name in ("0001_initial", "0004_patch", "0007_followup")
    }
    with (
        patch("posthog.management.commands.migrate_clickhouse.import_submodules", return_value=modules),
        patch.object(Command, "get_applied_migrations", return_value=set(already_applied)),
    ):
        names = [name for name, _ in Command().get_migrations(object(), upto)]
    assert names == expected


@pytest.mark.parametrize(
    "other_options",
    [
        pytest.param({}, id="would_apply_real_migrations"),
        pytest.param({"fake": True}, id="would_fake_applied_migrations"),
        pytest.param({"check": True}, id="check_without_plan_still_invalid"),
    ],
)
def test_print_sql_requires_plan_before_any_side_effects(
    other_options: dict[str, bool],
) -> None:
    # The flag's documented contract says --print-sql is only valid with --plan.
    # The original command otherwise silently runs the write-enabled branch.
    with patch(
        "posthog.management.commands.migrate_clickhouse.get_clickhouse_creds",
        side_effect=RuntimeError("unsafe credential lookup attempted"),
    ) as credential_lookup:
        with pytest.raises(CommandError, match=r"--print-sql requires --plan"):
            Command().migrate(
                CLICKHOUSE_URL, {**APPLY_OPTIONS, **other_options, "print_sql": True}
            )
    credential_lookup.assert_not_called()


def test_print_sql_with_plan_is_read_only(capsys: pytest.CaptureFixture[str]) -> None:
    creds = ClickHouseCredentials(user="migrations", password="synthetic-only")
    sql = SimpleNamespace(_sql="SELECT 123 AS flind_test")
    with (
        patch(
            "posthog.management.commands.migrate_clickhouse.get_clickhouse_creds",
            return_value=creds,
        ),
        patch("posthog.management.commands.migrate_clickhouse.Database") as database,
        patch.object(Command, "_create_database_if_not_exists") as create_database,
        patch.object(Command, "_create_migration_tracking_tables_if_not_exist") as create_tracking,
        patch.object(Command, "get_migrations", return_value=[("0001_test", [sql])]),
        patch.object(Command, "get_applied_migrations", return_value=set()),
    ):
        Command().migrate(
            CLICKHOUSE_URL, {**APPLY_OPTIONS, "plan": True, "print_sql": True}
        )
    output = capsys.readouterr().out
    assert "0001_test" in output
    assert "SELECT 123 AS flind_test" in output
    create_database.assert_not_called()
    create_tracking.assert_not_called()
    assert database.call_args.kwargs["readonly"] is True
    assert database.call_args.kwargs["autocreate"] is False
    database.return_value.migrate.assert_not_called()
    database.return_value.insert.assert_not_called()
