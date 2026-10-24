"""F3 Wave 15: seven safe service/utility npm workspaces, no registry rewrites."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import REPO_ROOT, inspect_packages, load_tracked_package_manifests

PATHS = (
    "nodejs/src/ingestion/pipelines/sessionreplay/ml-mirror-image-scrub-sidecar/package.json",
    "products/canvas/packages/canvas_builder/package.json",
    "products/visual_review/cli/package.json",
    "services/agent-proxy/package.json",
    "services/credentials-service/package.json",
    "services/oauth-proxy/package.json",
    "services/stripe-app/package.json",
)
OLD_SCOPE = "@post" + "hog/"


class ServiceToolsWave15Tests(unittest.TestCase):
    def test_seven_first_party_manifests_private(self) -> None:
        for path in PATHS:
            with self.subTest(path=path):
                manifest = json.loads((REPO_ROOT / path).read_text())
                self.assertTrue(manifest["name"].startswith("@flind/"))
                self.assertIs(manifest["private"], True)

    def test_workspaces_graph_keeps_all_existing_edges(self) -> None:
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(report["workspace_gate_passed"], report)
        self.assertEqual(report["unresolved_workspace_dependencies"], [])
        self.assertGreaterEqual(report["workspace_dependency_edges"], 261)
        self.assertGreaterEqual(len(report["flind_package_names"]), 139)
        self.assertLessEqual(len(report["remaining_legacy_package_names"]), 20)

    def test_no_exact_old_service_imports_in_tracked_source(self) -> None:
        old_ids = [OLD_SCOPE + json.loads((REPO_ROOT / path).read_text())["name"].split("/", 1)[1]
                   for path in PATHS]
        patterns = tuple(re.compile(re.escape(old) + r"(?![\w@-])") for old in old_ids)
        names = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT).decode().split("\0")
        ext = {".json", ".yml", ".yaml", ".toml", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".py", ".sh", ".md"}
        unexpected = []
        for name in names:
            if not name:
                continue
            path = REPO_ROOT / name
            if path.suffix not in ext:
                continue
            try:
                if not path.is_file() or path.stat().st_size > 3_000_000:
                    continue
                source = path.read_text()
            except (OSError, UnicodeError):
                continue
            if any(p.search(source) for p in patterns):
                unexpected.append(name)
        self.assertEqual(unexpected, [])

    def test_external_published_mcp_dependency_stays_intact(self) -> None:
        lock = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        # Published third-party package is NOT an internal workspace and cannot be rebranded.
        self.assertIn("'@posthog/mcp@0.23.0':", lock)
        self.assertNotIn("'@flind/mcp@0.23.0':", lock)

    def test_lockfile_has_no_wrong_first_party_registry_alias(self) -> None:
        lock = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        for path in PATHS:
            manifest = json.loads((REPO_ROOT / path).read_text())
            package = manifest["name"]
            with self.subTest(package=package):
                self.assertNotIn("  '" + package + "@", lock)


if __name__ == "__main__":
    unittest.main()
