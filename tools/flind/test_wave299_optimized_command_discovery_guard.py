"""Fail-closed original Django command discovery in normal and optimized runner modes."""
import ast
import pathlib
import unittest

RUNNERS = (
    "tools/flind/qualify_original_cli_real_0001_0020_schema_wave298.py",
    "tools/flind/qualify_original_cli_real_0001_0020_schema_optimized_wave298.py",
)


def command_guard(path):
    tree = ast.parse(pathlib.Path(path).read_text())
    source = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "LIVE_SOURCE" for target in node.targets)
    )
    parsed = ast.parse(source)
    guards = [
        node for node in parsed.body
        if isinstance(node, ast.If)
        and ast.unparse(node.test) == "get_commands().get('migrate_clickhouse') != 'posthog'"
    ]
    if len(guards) != 1 or len(guards[0].body) != 1 or not isinstance(guards[0].body[0], ast.Raise):
        raise AssertionError("missing fail-closed command registration guard")
    return guards[0]


class TestOptimizedCommandGuard(unittest.TestCase):
    def test_both_runners_fail_closed_under_optimization(self):
        for path in RUNNERS:
            with self.subTest(path=path):
                guard = command_guard(path)
                code = compile(
                    ast.fix_missing_locations(ast.Module(body=[guard], type_ignores=[])),
                    path, "exec", optimize=2,
                )
                for registered in ("posthog", "wrong-app", None):
                    with self.subTest(registered=registered):
                        namespace = {"get_commands": lambda: {"migrate_clickhouse": registered}}
                        if registered == "posthog":
                            exec(code, namespace)
                        else:
                            with self.assertRaisesRegex(
                                RuntimeError, "FLIND_W298_UNEXPECTED_MIGRATION_COMMAND"
                            ):
                                exec(code, namespace)


if __name__ == "__main__":
    unittest.main()
