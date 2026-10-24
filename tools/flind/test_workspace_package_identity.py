"""Core Flind pnpm workspace package identity and lockfile consistency.

This is deliberately independent of the full JS dependency installation.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_NAME = "@flind/frontend"
ROOT_NAME = "@flind/root"
LEGACY_FRONTEND = "@post" + "hog/frontend"
LEGACY_ROOT = "@post" + "hog/root"


class FlindWorkspacePackageTests(unittest.TestCase):
    def test_root_and_frontend_are_flind_named_and_private(self) -> None:
        for filename, name in (("package.json", ROOT_NAME), ("frontend/package.json", FRONTEND_NAME)):
            with self.subTest(file=filename):
                data = json.loads((ROOT / filename).read_text())
                self.assertEqual(data["name"], name)
                self.assertIs(data["private"], True)
                self.assertEqual(data["homepage"], "https://github.com/TheHalfMoon/Flind")
                self.assertEqual(data["bugs"]["url"], "https://github.com/TheHalfMoon/Flind/issues")
                self.assertEqual(data["repository"]["url"], "https://github.com/TheHalfMoon/Flind.git")
                self.assertEqual(data["author"], "Flind Contributors")

    def test_storybook_and_playwright_reference_exact_flind_frontend_workspace(self) -> None:
        for filename in ("common/storybook/package.json", "playwright/package.json"):
            with self.subTest(file=filename):
                data = json.loads((ROOT / filename).read_text())
                self.assertEqual(data["dependencies"][FRONTEND_NAME], "workspace:*")
                self.assertNotIn(LEGACY_FRONTEND, data["dependencies"])
                self.assertIn(FRONTEND_NAME, data["scripts"]["build:products"])

    def test_lockfile_uses_new_workspace_dependency_keys_and_existing_links(self) -> None:
        source = (ROOT / "pnpm-lock.yaml").read_text()
        self.assertNotIn(LEGACY_FRONTEND, source)
        self.assertIn(f"'{FRONTEND_NAME}':\n        specifier: workspace:*\n        version: link:../../frontend", source)
        self.assertIn(f"'{FRONTEND_NAME}':\n        specifier: workspace:*\n        version: link:../frontend", source)

    def test_core_build_commands_and_ci_filters_follow_new_package_names(self) -> None:
        paths = [
            "package.json", "frontend/package.json", "hogli.yaml", "Dockerfile",
            ".github/workflows/ci-frontend.yml", ".github/workflows/ci-e2e-playwright.yml",
            ".github/workflows/ci-dev-setup.yml",
            ".depot/workflows/ci-backend.yml", ".github/workflows/release-cli.yml",
            "bin/lint-complexity.mjs", "frontend/bin/build-app-url-manifest.mjs",
            "frontend/bin/typegen-file.mjs", "common/storybook/turbo.json",
            "tools/hogli-commands/hogli_commands/test_runner.py",
        ]
        for filename in paths:
            with self.subTest(file=filename):
                source = (ROOT / filename).read_text()
                self.assertNotIn(LEGACY_FRONTEND, source)
                self.assertNotIn(LEGACY_ROOT, source)
        root = json.loads((ROOT / "package.json").read_text())
        self.assertIn(FRONTEND_NAME, root["scripts"]["build:products"])
        self.assertIn(FRONTEND_NAME, root["scripts"]["test:unit"])

    def test_metadata_is_parseable_in_all_dependents(self) -> None:
        for filename in ("package.json", "frontend/package.json", "common/storybook/package.json", "playwright/package.json"):
            with self.subTest(file=filename):
                self.assertIsInstance(json.loads((ROOT / filename).read_text()), dict)


if __name__ == "__main__":
    unittest.main()
