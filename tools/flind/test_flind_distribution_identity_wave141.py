"""Guard the first-party Python *distribution* identity (not Django app-label migration)."""
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FlindDistributionIdentityWave141(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "pyproject.toml").open("rb") as f:
            cls.project = tomllib.load(f)
        with (ROOT / "uv.lock").open("rb") as f:
            cls.lock = tomllib.load(f)

    def test_root_project_is_flind(self):
        self.assertEqual(self.project["project"]["name"], "flind")
        self.assertEqual(self.project["project"]["version"], "0.0.0")

    def test_lock_manifest_resolves_flind_root(self):
        members = self.lock["manifest"]["members"]
        self.assertIn("flind", members)
        self.assertNotIn("posthog", members)
        roots = [p for p in self.lock["package"] if p["source"] == {"virtual": "."}]
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["name"], "flind")
        self.assertEqual(roots[0]["version"], self.project["project"]["version"])

    def test_conflict_resolution_owned_by_flind(self):
        conflicts = self.lock["conflicts"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual({x["package"] for x in conflicts[0]}, {"flind"})
        self.assertEqual({x["group"] for x in conflicts[0]}, {"inbox-ranking", "sentiment"})
        markers = "\n".join(self.lock["resolution-markers"])
        self.assertIn("flind", markers)
        self.assertNotIn("group-7-posthog-", markers)

    def test_python_pin_consistent_with_lock(self):
        self.assertEqual(self.project["project"]["requires-python"], self.lock["requires-python"])

    def test_dependency_identity_is_not_source_import_rename(self):
        # The runtime still owns Python imports under posthog.* until its
        # database migration/app-label conversion passes independent E2E.
        self.assertTrue((ROOT / "posthog" / "__init__.py").is_file())
        self.assertIn("PostHog", (ROOT / "LICENSE").read_text())


if __name__ == "__main__":
    unittest.main()
