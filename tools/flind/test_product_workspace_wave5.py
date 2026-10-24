"""F3 Wave 5: twenty first-party lightweight product workspace name gates."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import REPO_ROOT, inspect_packages, load_tracked_package_manifests

SUFFIXES = (
    "access-control", "account-audits", "aeo", "ai-gateway", "ai-training",
    "analytics-platform", "apm", "approvals", "authorization", "batch-exports",
    "commands", "context-layer", "core-events", "data-tools", "demo",
    "event-definitions", "exports", "field-notes", "games", "links",
)
OLD_SCOPE = "@post" + "hog/products-"
NEW_SCOPE = "@flind/products-"


class ProductWorkspaceWave5Tests(unittest.TestCase):
    def test_twenty_product_packages_are_private_and_flind_owned(self) -> None:
        manifests = dict(load_tracked_package_manifests(REPO_ROOT))
        existing = {doc.get("name"): (path, doc) for path, doc in manifests.items()}
        for suffix in SUFFIXES:
            with self.subTest(product=suffix):
                name = NEW_SCOPE + suffix
                self.assertIn(name, existing)
                self.assertIs(existing[name][1]["private"], True)
                self.assertNotIn(OLD_SCOPE + suffix, existing)

    def test_graph_preserves_expected_dependency_edges(self) -> None:
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(report["workspace_gate_passed"], report)
        self.assertGreaterEqual(report["workspace_dependency_edges"], 260)
        self.assertGreaterEqual(len(report["flind_package_names"]), 33)
        self.assertLessEqual(len(report["remaining_legacy_package_names"]), 126)
        self.assertEqual(report["unresolved_workspace_dependencies"], [])

    def test_frontend_dependencies_are_migrated_where_present(self) -> None:
        dependencies = json.loads((REPO_ROOT / "frontend/package.json").read_text())["dependencies"]
        for suffix in SUFFIXES:
            with self.subTest(suffix=suffix):
                self.assertNotIn(OLD_SCOPE + suffix, dependencies)
                if NEW_SCOPE + suffix in dependencies:
                    self.assertEqual(dependencies[NEW_SCOPE + suffix], "workspace:*")

    def test_lockfile_product_importers_are_first_party(self) -> None:
        lockfile = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        for suffix in SUFFIXES:
            with self.subTest(suffix=suffix):
                self.assertNotIn("'" + OLD_SCOPE + suffix + "':", lockfile)
                if "'" + NEW_SCOPE + suffix + "':" in lockfile:
                    self.assertIn("specifier: workspace:*", lockfile)

    def test_all_tracked_manifests_have_no_prior_selected_ids(self) -> None:
        for path, manifest in load_tracked_package_manifests(REPO_ROOT):
            with self.subTest(path=path):
                content = json.dumps(manifest)
                for suffix in SUFFIXES:
                    self.assertNotIn(OLD_SCOPE + suffix + '"', content)


if __name__ == "__main__":
    unittest.main()
