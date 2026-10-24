"""F3 Wave 14: shared agent/toolchain/workspace npm identity protection."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import (
    REPO_ROOT, inspect_packages, load_tracked_package_manifests,
)

OLD_SCOPE = "@post" + "hog/"
SIMPLE_NAMES = (
    "tailwind", "docs-onboarding", "agent-contracts", "agent",
    "enricher", "git", "harness", "quill-storybook",
    "quill-workspace", "quill-blocks", "quill-charts",
    "quill-components", "quill-primitives", "quill",
    "quill-tokens", "ai-research-v4-native",
    "batch-import-worker-scripts", "replay-anonymizer",
    "openapi-codegen", "workflow-plan",
)
SPECIAL = {
    "hogql-parser": "query-parser",
    "hogvm": "logicvm",
    "hogvm-node": "logicvm-node",
}
PAIRS = {
    **{OLD_SCOPE + old: "@flind/" + old for old in SIMPLE_NAMES},
    **{OLD_SCOPE + old: "@flind/" + new for old, new in SPECIAL.items()},
}


class SharedWorkspaceWave14Tests(unittest.TestCase):
    def test_all_23_package_names_are_flind_and_private(self) -> None:
        self.assertEqual(len(PAIRS), 23)
        packages = {doc.get("name"): (path, doc)
                    for path, doc in load_tracked_package_manifests(REPO_ROOT)}
        for old, new in PAIRS.items():
            with self.subTest(package=new):
                self.assertIn(new, packages)
                self.assertNotIn(old, packages)
                self.assertIs(packages[new][1].get("private"), True)

    def test_no_breakage_in_workspace_graph(self) -> None:
        result = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(result["workspace_gate_passed"], result)
        self.assertGreaterEqual(result["workspace_dependency_edges"], 261)
        self.assertEqual(result["unresolved_workspace_dependencies"], [])
        self.assertGreaterEqual(len(result["flind_package_names"]), 132)
        self.assertLessEqual(len(result["remaining_legacy_package_names"]), 27)

    def test_npm_lockfile_contains_no_exact_previous_names(self) -> None:
        source = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        for old in PAIRS:
            with self.subTest(package=old):
                self.assertIsNone(re.search(re.escape(old) + r"(?![\w-])", source))

    def test_repo_tsconfig_and_root_scripts_use_new_scope(self) -> None:
        tracked = (
            REPO_ROOT / "package.json",
            REPO_ROOT / "tsconfig.json",
            REPO_ROOT / "pnpm-workspace.yaml",
        )
        for path in tracked:
            if not path.is_file():
                continue
            with self.subTest(path=str(path)):
                source = path.read_text()
                for old in PAIRS:
                    self.assertIsNone(re.search(re.escape(old) + r"(?![\w-])", source))

    def test_exact_old_identifiers_are_not_left_in_tracked_source(self) -> None:
        names = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=REPO_ROOT,
        ).decode("utf-8").split("\0")
        extensions = {".json", ".jsonc", ".yaml", ".yml", ".toml",
                      ".mjs", ".cjs", ".js", ".jsx", ".ts", ".tsx",
                      ".py", ".md", ".mdx", ".sh", ".bash", ".txt",
                      ".mts", ".cts"}
        patterns = tuple(
            re.compile(re.escape(old) + r"(?![\w-])")
            for old in PAIRS
        )
        leaks = []
        for name in names:
            if not name:
                continue
            path = REPO_ROOT / name
            if path.suffix.lower() not in extensions and path.name not in (
                "Dockerfile", "Containerfile", "Makefile",
            ):
                continue
            try:
                if not path.is_file() or path.stat().st_size > 3_000_000:
                    continue
                text = path.read_text()
            except (OSError, UnicodeError):
                continue
            if any(p.search(text) for p in patterns):
                leaks.append(name)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
