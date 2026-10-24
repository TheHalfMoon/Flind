"""F3 Wave 17: local Node and MCP identities without changing published SDKs."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import REPO_ROOT, inspect_packages, load_tracked_package_manifests


class NodeMcpInternalWave17Tests(unittest.TestCase):
    def test_node_and_mcp_internal_manifests_are_flind_and_private(self) -> None:
        for filename, expected in (
            ("nodejs/package.json", "@flind/nodejs"),
            ("services/mcp/package.json", "@flind/mcp"),
        ):
            with self.subTest(path=filename):
                source = json.loads((REPO_ROOT / filename).read_text())
                self.assertEqual(source["name"], expected)
                self.assertIs(source.get("private"), True)

    def test_workspace_graph_keeps_dependencies_and_only_lemon_ui_remains(self) -> None:
        result = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(result["workspace_gate_passed"], result)
        self.assertEqual(result["unresolved_workspace_dependencies"], [])
        self.assertGreaterEqual(result["workspace_dependency_edges"], 261)
        self.assertGreaterEqual(len(result["flind_package_names"]), 158)
        self.assertEqual(result["remaining_legacy_package_names"], ["@posthog/lemon-ui"])

    def test_external_published_mcp_and_ui_packages_are_intact(self) -> None:
        lock = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        self.assertIn("'@posthog/mcp@0.23.0':", lock)
        self.assertIn("'@posthog/lemon-ui@0.0.0':", lock)
        self.assertNotIn("'@flind/mcp@0.23.0':", lock)
        self.assertNotIn("'@flind/lemon-ui@0.0.0':", lock)

    def test_internal_mcp_cli_filters_now_use_flind(self) -> None:
        for path in (
            REPO_ROOT / "services/mcp/Dockerfile",
            REPO_ROOT / "services/mcp/AGENTS.md",
            REPO_ROOT / "services/mcp/scripts/scaffold-yaml.ts",
        ):
            with self.subTest(path=str(path)):
                source = path.read_text()
                self.assertIn("@flind/mcp", source)
                self.assertNotIn("--filter=@post" + "hog/mcp", source)
                self.assertNotIn("--filter @post" + "hog/mcp", source)

    def test_exact_internal_nodejs_import_names_migrated(self) -> None:
        files = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT).decode().split("\0")
        pattern = re.compile(re.escape("@post" + "hog/nodejs") + r"(?![\w@-])")
        errors = []
        for name in files:
            if not name or Path(name).suffix not in {
                ".ts", ".tsx", ".js", ".json", ".yaml", ".yml", ".md", ".py", ".sh",
            }:
                continue
            path = REPO_ROOT / name
            try:
                if not path.is_file() or path.stat().st_size > 3_000_000:
                    continue
                source = path.read_text()
            except (OSError, UnicodeError):
                continue
            if pattern.search(source):
                errors.append(name)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
