"""Wave 99: desktop package scripts must target actual Flind workspaces."""
import json
from pathlib import Path
import re
import unittest

from tools.flind.check_workspace_links import REPO_ROOT, load_tracked_package_manifests


class DesktopFilterTargetsWave99(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifests = dict(load_tracked_package_manifests(REPO_ROOT))
        cls.names = {data.get("name"): (path, data) for path, data in cls.manifests.items() if data.get("name")}
        cls.scripts = json.loads((REPO_ROOT / "products/desktop/package.json").read_text())["scripts"]

    def test_dev_scripts_target_actual_agent_code_and_git_workspaces(self):
        for script, target in {
            "dev:agent": "@flind/agent",
            "dev:git": "@flind/git",
            "dev:code": "@flind/code",
        }.items():
            with self.subTest(script=script):
                self.assertIn(f"--filter {target} ", self.scripts[script])
                self.assertIn(target, self.names)
        self.assertIn("dev", self.names["@flind/agent"][1]["scripts"])
        self.assertIn("start", self.names["@flind/code"][1]["scripts"])

    def test_packaging_vitest_and_e2e_filters_select_code(self):
        for script in ("package", "test:vitest", "test:e2e", "test:e2e:headed"):
            with self.subTest(script=script):
                self.assertIn("--filter @flind/code ", self.scripts[script])
        for task in ("package", "test:e2e", "test:e2e:headed"):
            self.assertIn(task, self.names["@flind/code"][1]["scripts"])

    def test_bun_task_uses_only_real_existing_local_packages(self):
        self.assertEqual(self.scripts["test:bun"], "turbo test --filter=@flind/core")
        self.assertIn("@flind/core", self.names)
        self.assertIn("test", self.names["@flind/core"][1]["scripts"])
        self.assertNotIn("@posthog/cli", self.scripts["test:bun"])

    def test_every_literal_root_filter_points_to_a_named_package(self):
        # Literal package selectors in scripts are validated against actual
        # tracked source manifests, not guessed from a rebranding prefix.
        for script, cmd in self.scripts.items():
            candidates = re.findall(r"--filter(?:=|\s+)(@flind/[A-Za-z0-9_-]+)", cmd)
            for target in candidates:
                with self.subTest(script=script, target=target):
                    self.assertIn(target, self.names)

    def test_inherited_alias_filters_are_absent(self):
        for script, cmd in self.scripts.items():
            with self.subTest(script=script):
                self.assertNotRegex(cmd, r"--filter(?:=|\s+)(?:code|agent)(?:\s|$)")
                self.assertNotIn("--filter=@posthog/", cmd)


if __name__ == "__main__":
    unittest.main()
