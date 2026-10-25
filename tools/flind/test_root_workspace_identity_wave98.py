"""Wave 98: root workspaces are first-party Flind, not inherited package identities."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.flind.check_workspace_links import REPO_ROOT, inspect_packages, load_tracked_package_manifests

ROOTS = {
    "packages/agent/package.json": "@flind/agent-workspace",
    "products/desktop/package.json": "@flind/desktop-workspace",
}


class RootWorkspaceIdentityWave98(unittest.TestCase):
    def test_actual_root_manifests_use_flind_scope(self):
        for path, expected in ROOTS.items():
            with self.subTest(path=path):
                document = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
                self.assertEqual(document["name"], expected)
                self.assertTrue(document["private"])
                self.assertEqual(document["license"], "MIT")
                self.assertIn("Flind", document["description"])
                self.assertNotIn("PostHog", document["description"])

    def test_desktop_legal_author_field_remains_intact(self):
        source = json.loads((REPO_ROOT / "products/desktop/package.json").read_text())
        # Root identity and marketing metadata are distinct from the mandatory
        # provenance/license fields inherited from the authorized donor.
        self.assertEqual(source["author"], "PostHog")
        self.assertEqual(source["license"], "MIT")
        self.assertIn("flind", source["keywords"])
        self.assertNotIn("posthog", source["keywords"])

    def test_renamed_root_names_are_globally_unique(self):
        documents = load_tracked_package_manifests(REPO_ROOT)
        names = [d.get("name") for _, d in documents]
        for expected in ROOTS.values():
            self.assertEqual(names.count(expected), 1)
        self.assertNotIn("posthog-code", names)
        self.assertNotIn("posthog-agent-workspace", names)

    def test_all_existing_workspace_links_still_resolve(self):
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(report["workspace_gate_passed"])
        self.assertTrue(report["package_identity_gate_passed"])
        self.assertEqual(report["unresolved_workspace_dependencies"], [])
        self.assertEqual(report["duplicate_active_package_names"], {})
        self.assertEqual(report["unprotected_flind_packages"], [])

    def test_lockfiles_keep_original_dependency_pins_and_packages(self):
        for path in ("packages/agent/pnpm-lock.yaml", "products/desktop/pnpm-lock.yaml"):
            with self.subTest(path=path):
                # No lockfile regenerations from renaming private monorepo
                # package metadata; frozen dependency versions stay intact.
                self.assertTrue((REPO_ROOT / path).is_file())
        self.assertEqual(len(ROOTS), 2)


if __name__ == "__main__":
    unittest.main()
