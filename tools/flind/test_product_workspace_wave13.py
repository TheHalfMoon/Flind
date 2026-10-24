"""F3 Wave 13: all product-prefixed npm workspaces have Flind identities."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import (
    REPO_ROOT, inspect_packages, load_tracked_package_manifests,
)

OLD_PREFIX = "@post" + "hog/products-"
NEW_PREFIX = "@flind/products-"
SPECIAL_PRODUCTS = {
    "products/posthog_ai/package.json": "@flind/products-flind-ai",
    "products/stamphog/package.json": "@flind/products-stamp",
    "products/review_hog/package.json": "@flind/products-review",
}


class ProductWorkspacesWave13Tests(unittest.TestCase):
    def test_no_remaining_product_workspace_uses_the_previous_scope(self) -> None:
        items = list(load_tracked_package_manifests(REPO_ROOT))
        self.assertEqual(len(items), 169)
        names = [manifest.get("name", "") for _, manifest in items]
        self.assertFalse([name for name in names if name.startswith(OLD_PREFIX)])
        self.assertGreaterEqual(sum(name.startswith(NEW_PREFIX) for name in names), 98)

    def test_all_first_party_product_manifests_are_private(self) -> None:
        items = list(load_tracked_package_manifests(REPO_ROOT))
        for path, manifest in items:
            name = manifest.get("name", "")
            if name.startswith(NEW_PREFIX):
                with self.subTest(name=name):
                    self.assertIs(manifest.get("private"), True, path)

    def test_old_brand_names_inside_the_package_id_are_replaced(self) -> None:
        for path, expected in SPECIAL_PRODUCTS.items():
            with self.subTest(path=path):
                manifest = json.loads((REPO_ROOT / path).read_text())
                self.assertEqual(manifest.get("name"), expected)
                self.assertIs(manifest.get("private"), True)

    def test_dependency_graph_and_migration_counts(self) -> None:
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(report["workspace_gate_passed"], report)
        self.assertEqual(report["unresolved_workspace_dependencies"], [])
        self.assertGreaterEqual(report["workspace_dependency_edges"], 260)
        self.assertGreaterEqual(len(report["flind_package_names"]), 109)
        self.assertLessEqual(len(report["remaining_legacy_package_names"]), 50)

    def test_lockfile_and_frontend_manifest_have_no_old_product_prefix(self) -> None:
        for path in ("pnpm-lock.yaml", "frontend/package.json"):
            with self.subTest(path=path):
                text = (REPO_ROOT / path).read_text()
                self.assertNotIn(OLD_PREFIX, text)

    def test_product_source_imports_no_longer_use_old_product_scope(self) -> None:
        files = subprocess.check_output(
            ["git", "ls-files", "-z", "products", "frontend", "packages", "services", "nodejs"],
            cwd=REPO_ROOT,
        ).decode("utf-8").split("\0")
        extensions = {".json", ".jsonc", ".yaml", ".yml", ".js",
                      ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py",
                      ".toml", ".sh", ".mts", ".cts"}
        unexpected = []
        for name in files:
            if not name:
                continue
            path = REPO_ROOT / name
            if path.suffix.lower() not in extensions:
                continue
            try:
                if not path.is_file() or path.stat().st_size > 3_000_000:
                    continue
                source = path.read_text()
            except (OSError, UnicodeError):
                continue
            if OLD_PREFIX in source:
                unexpected.append(name)
        self.assertEqual(unexpected, [])


if __name__ == "__main__":
    unittest.main()
