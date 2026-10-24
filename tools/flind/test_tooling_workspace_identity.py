"""First-party Flind Storybook and Playwright package wiring tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY_STORYBOOK = "@post" + "hog/storybook"
LEGACY_PLAYWRIGHT = "@post" + "hog/playwright"


class FlindToolingWorkspaceTests(unittest.TestCase):
    def test_storybook_playwright_package_ids_are_private(self) -> None:
        for name, expected in (
            ("common/storybook/package.json", "@flind/storybook"),
            ("playwright/package.json", "@flind/playwright"),
        ):
            with self.subTest(name=name):
                doc = json.loads((ROOT / name).read_text())
                self.assertEqual(doc["name"], expected)
                self.assertIs(doc["private"], True)
                self.assertEqual(doc["dependencies"]["@flind/frontend"], "workspace:*")

    def test_ci_and_dev_scripts_only_use_flind_tooling_ids(self) -> None:
        files = (
            ".github/workflows/ci-storybook.yml",
            ".github/workflows/ci-e2e-playwright.yml",
            ".github/workflows/ci-frontend.yml",
            ".github/scripts/verify-storybook-new-stories.sh",
            ".github/scripts/verify-playwright-new-tests-and-snapshots.sh",
            "bin/mprocs.yaml",
            "bin/mprocs-e2e.yaml",
            "package.json",
            "common/storybook/.storybook/plugins/vite-frontend-resolve-plugin.ts",
        )
        for name in files:
            with self.subTest(name=name):
                source = (ROOT / name).read_text()
                self.assertNotIn(LEGACY_STORYBOOK, source)
                self.assertNotIn(LEGACY_PLAYWRIGHT, source)

    def test_workspace_package_names_resolve_with_no_new_registry_package(self) -> None:
        for package, name in (("common/storybook/package.json", "@flind/storybook"),
                              ("playwright/package.json", "@flind/playwright")):
            doc = json.loads((ROOT / package).read_text())
            self.assertEqual(doc["name"], name)
            self.assertEqual(doc["dependencies"]["@flind/frontend"], "workspace:*")
            self.assertNotIn(LEGACY_PLAYWRIGHT, doc["dependencies"])
            self.assertNotIn(LEGACY_STORYBOOK, doc["dependencies"])

    def test_lockfile_keeps_path_based_importers(self) -> None:
        lock = (ROOT / "pnpm-lock.yaml").read_text()
        self.assertIn("  common/storybook:\n", lock)
        self.assertIn("  playwright:\n", lock)
        self.assertIn("'@flind/frontend':", lock)
        self.assertNotIn(LEGACY_STORYBOOK, lock)
        self.assertNotIn(LEGACY_PLAYWRIGHT, lock)


if __name__ == "__main__":
    unittest.main()
