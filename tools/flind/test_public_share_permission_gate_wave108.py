"""Wave 108 — public sharing must not swallow Django/DRF permission denials.

Execute the actual product authorization function AST with controlled query
runners. No database, cloud, mocked copy of the decision tree, or credentials.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DjangoPermissionDenied(Exception):
    pass


class DRFPermissionDenied(Exception):
    pass


class UserAccessControlError(Exception):
    def __init__(self, resource):
        self.resource = resource


class TableAccessDeniedError(Exception):
    def __init__(self, table_name):
        self.table_name = table_name


class QueryContext:
    def __init__(self, *, team_id, team, user, enable_select_queries, modifiers):
        self.team_id = team_id


class Modifiers:
    def model_dump_json(self):
        return '{"safe":true}'


def load_actual_function(path, name, dependencies):
    source = ROOT / path
    module = ast.parse(source.read_text())
    match = [obj for obj in module.body if isinstance(obj, ast.FunctionDef) and obj.name == name]
    assert len(match) == 1, f"{name} is missing or ambiguous"
    node = match[0]
    node.decorator_list = []
    result_module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), node],
        type_ignores=[],
    )
    ast.fix_missing_locations(result_module)
    exec(compile(result_module, str(source), "exec"), dependencies)
    return dependencies[name]


class PublicSharingPermissionWave108(unittest.TestCase):
    def invoke(self, *, event=None, runner_none=False, print_failure=None):
        user = object()
        team = SimpleNamespace(pk=101)
        counts = {"checked": 0, "compiled": 0, "runner": 0}

        class Runner:
            modifiers = {}

            def validate_query_runner_access(self, current_user):
                self.assert_user(current_user)
                counts["checked"] += 1
                if event is not None:
                    raise event

            @staticmethod
            def assert_user(actual_user):
                assert actual_user is user

            def to_query(self):
                return {"kind": "HogQLQuery"}

        def runner_getter(query, got_team, *, user=None):
            counts["runner"] += 1
            if isinstance(event, BaseException) and isinstance(event, QueryLookupError):
                raise event
            return None if runner_none else Runner()

        def printer(query, *, context, dialect):
            counts["compiled"] += 1
            self.assertEqual(context.team_id, team.pk)
            self.assertEqual(dialect, "clickhouse")
            if print_failure:
                raise print_failure

        dependencies = {
            "HogQLContext": QueryContext,
            "TableAccessDeniedError": TableAccessDeniedError,
            "UserAccessControlError": UserAccessControlError,
            "DjangoPermissionDenied": DjangoPermissionDenied,
            "DRFPermissionDenied": DRFPermissionDenied,
            "create_default_modifiers_for_user": lambda *args: Modifiers(),
            "get_query_runner_or_none": runner_getter,
            "prepare_ast_for_printing": printer,
        }
        fn = load_actual_function("posthog/api/query_access_check.py", "denied_query_resources", dependencies)
        return fn, user, team, counts

    def test_django_permission_denied_propagates_instead_of_allowing_share(self):
        fn, user, team, counts = self.invoke(event=DjangoPermissionDenied("private"))
        with self.assertRaises(DjangoPermissionDenied):
            fn(user, team, [{"kind": "AccountsQuery"}])
        self.assertEqual(counts["checked"], 1)

    def test_drf_permission_denied_propagates_instead_of_allowing_share(self):
        fn, user, team, counts = self.invoke(event=DRFPermissionDenied("private"))
        with self.assertRaises(DRFPermissionDenied):
            fn(user, team, [{"kind": "AccountsQuery"}])
        self.assertEqual(counts["checked"], 1)

    def test_django_permission_denied_during_sql_compile_propagates(self):
        fn, user, team, _ = self.invoke(print_failure=DjangoPermissionDenied("private query"))
        with self.assertRaises(DjangoPermissionDenied):
            fn(user, team, [{"kind": "DataTableNode"}])

    def test_drf_permission_denied_during_sql_compile_propagates(self):
        fn, user, team, _ = self.invoke(print_failure=DRFPermissionDenied("private query"))
        with self.assertRaises(DRFPermissionDenied):
            fn(user, team, [{"kind": "DataTableNode"}])

    def test_table_access_denial_retains_specific_name(self):
        fn, user, team, _ = self.invoke(event=TableAccessDeniedError("restricted_table"))
        self.assertEqual(fn(user, team, [{"kind": "DataTableNode"}]), ["restricted_table"])

    def test_resource_access_denial_retains_specific_name(self):
        fn, user, team, _ = self.invoke(event=UserAccessControlError("sensitive_resource"))
        self.assertEqual(fn(user, team, [{"kind": "AccountsQuery"}]), ["sensitive_resource"])

    def test_invalid_query_without_auth_error_still_does_not_block_publishing(self):
        fn, user, team, _ = self.invoke(print_failure=ValueError("broken syntax"))
        self.assertEqual(fn(user, team, [{"kind": "HogQLQuery", "query": "SELECT FROM"}]), [])

    def test_query_runner_with_no_match_remains_unchanged(self):
        fn, user, team, _ = self.invoke(runner_none=True)
        self.assertEqual(fn(user, team, [{"kind": "UnsupportedQuery"}]), [])

    def test_supported_query_without_denials_still_passes(self):
        fn, user, team, counts = self.invoke()
        self.assertEqual(fn(user, team, [{"kind": "HogQLQuery"}]), [])
        self.assertEqual(counts["compiled"], 1)

    def test_empty_query_collection_fast_path(self):
        fn, user, team, counts = self.invoke()
        self.assertEqual(fn(user, team, []), [])
        self.assertEqual(counts["runner"], 0)

    def test_share_enable_gate_propagates_permission_denial(self):
        # The actual public share route uses denied_resources_in_share(), so
        # a PermissionDenied from the query gate must abort the enable path.
        def reject(*args):
            raise DRFPermissionDenied("denied by query")
        fn = load_actual_function(
            "posthog/api/sharing_publish_gate.py",
            "denied_resources_in_share",
            {
                "denied_query_resources": reject,
                "_queries_exposed_by": lambda config: [{"kind": "AccountsQuery"}],
            },
        )
        with self.assertRaises(DRFPermissionDenied):
            fn(object(), object(), SimpleNamespace(dashboard=None))


class QueryLookupError(Exception):
    pass


if __name__ == "__main__":
    unittest.main()
