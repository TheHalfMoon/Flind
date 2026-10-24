"""F3 Wave 4: exact, copy-safe internal workspace package migration gates."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import REPO_ROOT, inspect_packages, load_tracked_package_manifests

PACKAGE_PATHS = {
    "esbuilder": "common/esbuilder/package.json",
    "owners-yaml": "packages/owners-yaml/package.json",
    "plugin-transpiler": "common/plugin_transpiler/package.json",
    "llm-normalizer": "packages/llm-normalizer/package.json",
    "replay-shared": "common/replay-shared/package.json",
    "replay-headless": "common/replay-headless/package.json",
    "products-annotations": "products/annotations/package.json",
    "products-customer-analytics": "products/customer_analytics/package.json",
}
PREVIOUS_SCOPE = "@post" + "hog/"
FIRST_PARTY_SCOPE = "@flind/"


class InternalWorkspaceMigrationWave4Tests(unittest.TestCase):
    def test_eight_renamed_package_manifests_are_private(self) -> None:
        for suffix, relative_path in PACKAGE_PATHS.items():
            with self.subTest(package=suffix):
                manifest = json.loads((REPO_ROOT / relative_path).read_text())
                self.assertEqual(manifest["name"], FIRST_PARTY_SCOPE + suffix)
                self.assertIs(manifest["private"], True)

    def test_graph_retains_all_workspace_dependency_edges(self) -> None:
        result = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(result["workspace_gate_passed"], result)
        self.assertGreaterEqual(result["workspace_dependency_edges"], 260)
        self.assertLessEqual(len(result["remaining_legacy_package_names"]), 146)
        for name in PACKAGE_PATHS:
            self.assertIn(FIRST_PARTY_SCOPE + name, result["flind_package_names"])
        self.assertGreaterEqual(len(result["flind_package_names"]), 13)

    def test_lockfile_workspace_importers_follow_exact_renames(self) -> None:
        lock = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        for name in (
            "esbuilder", "llm-normalizer", "replay-shared", "replay-headless",
            "products-annotations", "products-customer-analytics",
        ):
            with self.subTest(package=name):
                self.assertIn("'" + FIRST_PARTY_SCOPE + name + "':", lock)
                self.assertNotIn("'" + PREVIOUS_SCOPE + name + "':", lock)
        self.assertIn("version: link:../replay-shared", lock)
        self.assertIn("version: link:../packages/llm-normalizer", lock)

    def test_internal_imports_use_first_party_package_ids(self) -> None:
        expectations = {
            "frontend/build.mjs": ["esbuilder"],
            "frontend/vite.config.mts": ["llm-normalizer"],
            "tsconfig.json": ["llm-normalizer", "replay-shared"],
            "common/replay-headless/src/data-loader.ts": ["replay-shared"],
            "nodejs/src/session-replay/recording-rasterizer/capture/player.ts": ["replay-headless"],
            ".github/scripts/turbo-discover.js": ["owners-yaml"],
        }
        for file, names in expectations.items():
            with self.subTest(file=file):
                source = (REPO_ROOT / file).read_text()
                for name in names:
                    self.assertIn(FIRST_PARTY_SCOPE + name, source)
                    self.assertNotIn(PREVIOUS_SCOPE + name, source)

    def test_no_exact_legacy_names_remain_in_tracked_text(self) -> None:
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=REPO_ROOT
        ).decode("utf-8").split("\0")
        extensions = {".json", ".jsonc", ".yml", ".yaml", ".toml", ".mjs", ".cjs",
                      ".js", ".jsx", ".ts", ".tsx", ".py", ".md", ".mdx",
                      ".sh", ".bash", ".txt", ".mts", ".cts"}
        old_names = tuple(PREVIOUS_SCOPE + suffix for suffix in PACKAGE_PATHS)
        patterns = tuple(re.compile(re.escape(old) + r"(?![\w-])") for old in old_names)
        dangling = []
        for name in tracked:
            if not name:
                continue
            file = REPO_ROOT / name
            if file.suffix not in extensions and file.name not in ("Dockerfile", "Makefile", "Containerfile"):
                continue
            try:
                if not file.is_file() or file.stat().st_size > 3_000_000:
                    continue
                content = file.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if any(pattern.search(content) for pattern in patterns):
                dangling.append(name)
        self.assertEqual(dangling, [])


if __name__ == "__main__":
    unittest.main()
