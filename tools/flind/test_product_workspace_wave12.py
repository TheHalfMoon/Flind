"""F3 Wave 12: product-workspace npm ID migration and dependency protection."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import (
    REPO_ROOT, inspect_packages, load_tracked_package_manifests,
)

SUFFIXES = (
    "actions", "ai-observability", "alerts", "alerts-platform", "autoresearch",
    "billing", "billing-alerts", "business-intelligence", "business-knowledge",
    "canvas", "cdp", "cohorts", "conversations", "cross-project-dashboards",
    "dashboards", "data-catalog", "data-modeling", "data-quality",
    "data-warehouse", "early-access-features", "endpoints",
    "engineering-analytics", "error-tracking", "experiments", "feature-flags",
    "groups", "growth", "legal-documents", "live-debugger", "llm-analytics",
    "logs", "managed-migrations", "managed-warehouse", "marketing-analytics",
    "mcp-analytics", "mcp-registry", "mcp-store",
)
FIRST_PARTY = "@flind/products-"
INHERITED = "@post" + "hog/products-"


class ProductWorkspacesWave12Tests(unittest.TestCase):
    def test_migrated_37_manifests_are_first_party_and_private(self) -> None:
        source = dict(load_tracked_package_manifests(REPO_ROOT))
        packages = {entry.get("name"): (file, entry) for file, entry in source.items()}
        self.assertEqual(len(SUFFIXES), 37)
        for suffix in SUFFIXES:
            with self.subTest(suffix=suffix):
                name = FIRST_PARTY + suffix
                self.assertIn(name, packages)
                path, manifest = packages[name]
                self.assertIs(manifest.get("private"), True, path)
                self.assertNotIn(INHERITED + suffix, packages)

    def test_all_workspace_links_still_resolve(self) -> None:
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(report["workspace_gate_passed"], report)
        self.assertGreaterEqual(report["workspace_dependency_edges"], 260)
        self.assertEqual(report["unresolved_workspace_dependencies"], [])
        self.assertGreaterEqual(len(report["flind_package_names"]), 70)
        self.assertLessEqual(len(report["remaining_legacy_package_names"]), 89)

    def test_lockfile_references_use_first_party_package_names(self) -> None:
        lock = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        for suffix in SUFFIXES:
            with self.subTest(suffix=suffix):
                previous = INHERITED + suffix
                self.assertIsNone(
                    re.search(re.escape(previous) + r"(?![\w-])", lock),
                    f"old exact package ID in pnpm-lock.yaml: {previous}",
                )

    def test_frontend_manifests_have_no_prior_product_ids(self) -> None:
        source = (REPO_ROOT / "frontend/package.json").read_text()
        for suffix in SUFFIXES:
            with self.subTest(suffix=suffix):
                self.assertIsNone(re.search(re.escape(INHERITED + suffix) + r"(?![\w-])", source))

    def test_no_exact_legacy_ids_in_tracked_source(self) -> None:
        paths = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=REPO_ROOT,
        ).decode("utf-8").split("\0")
        suffixes = {".json", ".jsonc", ".yml", ".yaml", ".toml", ".mjs",
                    ".cjs", ".js", ".jsx", ".ts", ".tsx", ".py", ".md",
                    ".mdx", ".sh", ".bash", ".txt", ".mts", ".cts"}
        patterns = [
            re.compile(re.escape(INHERITED + suffix) + r"(?![\w-])")
            for suffix in SUFFIXES
        ]
        unexpected = []
        for name in paths:
            if not name:
                continue
            path = REPO_ROOT / name
            if path.suffix.lower() not in suffixes and path.name not in (
                "Dockerfile", "Containerfile", "Makefile",
            ):
                continue
            try:
                if not path.is_file() or path.stat().st_size > 3_000_000:
                    continue
                source = path.read_text()
            except (OSError, UnicodeError):
                continue
            if any(pattern.search(source) for pattern in patterns):
                unexpected.append(name)
        self.assertEqual(unexpected, [])


if __name__ == "__main__":
    unittest.main()
