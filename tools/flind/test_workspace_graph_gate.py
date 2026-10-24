"""Regression checks for the Flind workspace migration admission gate."""
from __future__ import annotations

import unittest

from tools.flind.check_workspace_links import inspect_packages, load_tracked_package_manifests, REPO_ROOT


class WorkspaceGraphGateTests(unittest.TestCase):
    def test_current_workspace_graph_has_no_dangling_links(self) -> None:
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(report["workspace_gate_passed"], report)
        self.assertEqual(report["unresolved_workspace_dependencies"], [])
        self.assertEqual(report["duplicate_active_package_names"], {})
        self.assertEqual(report["unprotected_flind_packages"], [])
        self.assertGreater(report["workspace_dependency_edges"], 0)

    def test_current_root_frontend_storybook_playwright_are_present(self) -> None:
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        for name in ("@flind/root", "@flind/frontend", "@flind/storybook", "@flind/playwright"):
            self.assertIn(name, report["flind_package_names"])

    def test_unknown_workspace_dependency_blocks_migration(self) -> None:
        report = inspect_packages([
            ("package.json", {"name": "@flind/root", "private": True, "dependencies": {"@flind/missing": "workspace:*"}})
        ])
        self.assertFalse(report["workspace_gate_passed"])
        self.assertEqual(report["unresolved_workspace_dependencies"][0]["dependency"], "@flind/missing")

    def test_duplicate_active_package_name_blocks_migration(self) -> None:
        report = inspect_packages([
            ("a/package.json", {"name": "@flind/library", "private": True}),
            ("b/package.json", {"name": "@flind/library", "private": True}),
        ])
        self.assertFalse(report["workspace_gate_passed"])
        self.assertIn("@flind/library", report["duplicate_active_package_names"])

    def test_unprotected_flind_package_blocks_migration(self) -> None:
        report = inspect_packages([
            ("package.json", {"name": "@flind/root", "private": False}),
        ])
        self.assertFalse(report["workspace_gate_passed"])
        self.assertEqual(report["unprotected_flind_packages"][0]["name"], "@flind/root")

    def test_nested_ci_action_name_collision_is_not_workspace_collision(self) -> None:
        report = inspect_packages([
            (".github/actions/paths-filter/package.json", {"name": "paths-filter"}),
            (".depot/actions/paths-filter/package.json", {"name": "paths-filter"}),
            ("frontend/package.json", {"name": "@flind/frontend", "private": True}),
        ])
        self.assertTrue(report["workspace_gate_passed"], report)

    def test_remaining_legacy_packages_are_not_misreported_as_complete(self) -> None:
        report = inspect_packages([
            ("package.json", {"name": "@flind/root", "private": True}),
            ("some/legacy/package.json", {"name": "@post" + "hog/legacy", "private": True}),
        ])
        self.assertTrue(report["workspace_gate_passed"])
        self.assertFalse(report["package_identity_gate_passed"])
        self.assertEqual(len(report["remaining_legacy_package_names"]), 1)


if __name__ == "__main__":
    unittest.main()
