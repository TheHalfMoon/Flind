"""Wave292: keep child failure reporting independent of unrelated scratch paths."""
from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNERS = (
    "tools/flind/qualify_original_cli_real_0001_0007_wave291.py",
    "tools/flind/qualify_original_cli_real_0001_0007_optimized_wave291.py",
)


def failure_branch(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Attribute)
        and isinstance(node.test.value, ast.Name)
        and node.test.value.id == "result"
        and node.test.attr == "returncode"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one child failure branch: {path}")
    module = ast.fix_missing_locations(ast.Module(body=[matches[0]], type_ignores=[]))
    return compile(module, str(path), "exec")


class Wave292ChildFailureIsolation(unittest.TestCase):
    def test_failure_keeps_original_error_and_does_not_write_elsewhere(self):
        with TemporaryDirectory(prefix="flind-wave292-") as directory:
            root = Path(directory)
            for name in RUNNERS:
                with self.subTest(runner=name):
                    code = failure_branch(ROOT / name)
                    result = SimpleNamespace(returncode=2, stderr="SYNTHETIC_CHILD_FAILURE\n")
                    with self.assertRaisesRegex(RuntimeError, "real_original_django_apply_failed_SYNTHETIC_CHILD_FAILURE"):
                        exec(code, {"result": result, "ROOT": root})
                    self.assertEqual(list(root.iterdir()), [])

    def test_success_branch_is_noop(self):
        with TemporaryDirectory(prefix="flind-wave292-") as directory:
            root = Path(directory)
            for name in RUNNERS:
                with self.subTest(runner=name):
                    code = failure_branch(ROOT / name)
                    exec(code, {"result": SimpleNamespace(returncode=0, stderr=""), "ROOT": root})
                    self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
