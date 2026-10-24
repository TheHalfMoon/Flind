"""Wave 16: first-party Desktop internal package ID migration regression."""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from tools.flind.check_workspace_links import REPO_ROOT, inspect_packages, load_tracked_package_manifests

DESKTOP_ROOT = REPO_ROOT / "products/desktop"
OLD = "@post" + "hog/"
REBRANDED_MOBILE = "@flind/mobile-studio"


class DesktopWorkspaceWave16Tests(unittest.TestCase):
    def test_all_17_desktop_manifests_private_and_first_party(self) -> None:
        paths = [
            Path(p) for p in subprocess.check_output(
                ["git", "ls-files", "-z", "products/desktop"],
                cwd=REPO_ROOT,
            ).decode().split("\0")
            if p.endswith("package.json")
        ]
        migrated = []
        for path in paths:
            data = json.loads((REPO_ROOT / path).read_text())
            name = data.get("name", "")
            if name.startswith("@flind/"):
                migrated.append(name)
                self.assertIs(data.get("private"), True, path)
            self.assertFalse(name.startswith(OLD), (path, name))
        self.assertGreaterEqual(len(migrated), 18)
        self.assertIn(REBRANDED_MOBILE, migrated)

    def test_workspace_graph_no_broken_links(self) -> None:
        report = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(report["workspace_gate_passed"], report)
        self.assertEqual(report["unresolved_workspace_dependencies"], [])
        self.assertGreaterEqual(report["workspace_dependency_edges"], 261)
        self.assertGreaterEqual(len(report["flind_package_names"]), 156)
        self.assertLessEqual(len(report["remaining_legacy_package_names"]), 3)

    def test_lockfile_uses_first_party_desktop_internal_package_names(self) -> None:
        lock = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        for path in DESKTOP_ROOT.rglob("package.json"):
            if "node_modules" in path.parts:
                continue
            data = json.loads(path.read_text())
            name = data.get("name", "")
            if name.startswith("@flind/"):
                with self.subTest(name=name):
                    self.assertNotIn("  '" + name + "@", lock)

    def test_desktop_tracked_source_imports_do_not_refer_to_legacy_scope(self) -> None:
        names = subprocess.check_output(
            ["git", "ls-files", "-z", "products/desktop"],
            cwd=REPO_ROOT,
        ).decode().split("\0")
        extensions = {".ts", ".tsx", ".js", ".jsx", ".json", ".mjs",
                      ".yaml", ".yml", ".toml", ".md"}
        unexpected = []
        for name in names:
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
            if name == "products/desktop/pnpm-lock.yaml":
                # This is the published SDK's external registry dependency,
                # not the first-party @flind/core workspace package. Four
                # specific edges and owners are verified by Wave 33 tests.
                source = re.sub(
                    r"(?m)^      '@posthog/core': 1\.60\.(?:0|1)$",
                    "",
                    source,
                )
            if OLD in source:
                # Other published source-project dependencies can be legitimate;
                # flag only the specific internal Desktop package prefixes.
                for package in (
                    "api-client", "core", "di", "electron-trpc", "host-router",
                    "host-trpc", "platform", "shared", "ui", "workspace-client",
                    "workspace-server", "tsup-config", "tsconfig", "code",
                    "mobile", "mobilehog", "web",
                ):
                    pattern = re.compile(re.escape(OLD + package) + r"(?![\w@-])")
                    if pattern.search(source):
                        unexpected.append(name)
                        break
        self.assertEqual(unexpected, [])

    def test_external_versioned_registry_dependencies_not_relabeled(self) -> None:
        lock = (REPO_ROOT / "pnpm-lock.yaml").read_text()
        self.assertIn("'@posthog/mcp@0.23.0':", lock)


if __name__ == "__main__":
    unittest.main()
