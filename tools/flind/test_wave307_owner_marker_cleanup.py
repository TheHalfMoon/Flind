"""Fail-closed cleanup tests for both owner-only Wave306 qualification runners.

No product imports, network, database, or external services. Tests execute only the
original runner's main() AST in a temporary synthetic directory.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

RUNNERS = (
    "qualify_original_cli_real_0001_0030_wave306.py",
    "qualify_original_cli_real_0001_0030_optimized_wave306.py",
)


def load_main(source_path: Path, scratch: Path, marker: str, optimize: int):
    source = source_path.read_text(encoding="utf-8")
    parsed = ast.parse(source, filename=str(source_path))
    methods = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(methods) != 1:
        raise RuntimeError("expected exactly one first-party main()")
    node = methods[0]
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))

    def fail_preflight():
        raise RuntimeError("synthetic_preflight_failure")

    namespace = {
        "run": fail_preflight,
        "REPORT": {},
        "children": [],
        "stop_all": lambda: None,
        "free_space": lambda: 2 * 1024**3,
        "SCRATCH": scratch,
        "ROOT": scratch.parent,
        "MARKER": marker,
        "shutil": shutil,
        "json": json,
    }
    exec(compile(module, str(source_path), "exec", optimize=optimize), namespace)
    return namespace["main"], namespace["REPORT"]


class OwnerMarkerCleanupTests(unittest.TestCase):
    def test_preflight_failure_never_masks_blocker_or_removes_unowned_scratch(self):
        source_dir = Path(__file__).resolve().parent
        for runner in RUNNERS:
            for kind in ("missing", "wrong", "symlink", "valid"):
                for optimize in (0, 2):
                    with self.subTest(runner=runner, marker=kind, optimize=optimize), tempfile.TemporaryDirectory() as root:
                        scratch = Path(root) / "flind-owned-synthetic"
                        scratch.mkdir()
                        sentinel = scratch / "sentinel.txt"
                        sentinel.write_text("must-preserve-unless-owned", encoding="utf-8")
                        marker_text = "FLIND_WAVE307_OWNER_ONLY_SYNTHETIC_TEST_V1\n"
                        marker = scratch / ".flind-owner-only"
                        if kind == "wrong":
                            marker.write_text("OTHER_OWNER\n", encoding="utf-8")
                        elif kind == "valid":
                            marker.write_text(marker_text, encoding="utf-8")
                        elif kind == "symlink":
                            outside = Path(root) / "external-marker"
                            outside.write_text(marker_text, encoding="utf-8")
                            marker.symlink_to(outside)
                        main, report = load_main(source_dir / runner, scratch, marker_text, optimize)
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output):
                            exit_code = main()
                        self.assertEqual(exit_code, 2)
                        self.assertEqual(report["blocker"], "synthetic_preflight_failure")
                        self.assertTrue(report["owned_children_stopped"])
                        self.assertEqual(report["owner_scratch_cleaned"], kind == "valid")
                        self.assertEqual(json.loads(output.getvalue())["blocker"], "synthetic_preflight_failure")
                        self.assertEqual(scratch.exists(), kind != "valid")
                        if kind != "valid":
                            self.assertEqual(sentinel.read_text(), "must-preserve-unless-owned")


if __name__ == "__main__":
    unittest.main()
