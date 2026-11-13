"""Fail closed if an inherited upstream release/publish workflow is re-enabled.

Checks that the exact original Git blobs remain in a non-Action directory,
without becoming runnable workflows or being referenced as reusable workflows.
Does not claim to audit every remaining CD pipeline in the repository.
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE = ROOT / ".github" / "workflows"
PARKED = ROOT / ".github" / "quarantined-release-workflows"
MANIFEST = json.loads(
    (ROOT / "tools/flind/quarantined_release_workflows.json").read_text(encoding="utf8")
)
EXPECTED_NAMES = {
    "build-deltalite.yml",
    "build-hobby-installer.yml",
    "build-hogql-parser-npm.yml",
    "build-hogql-parser-rs.yml",
    "build-hogql-parser.yml",
    "build-livestream-tui.yml",
    "build-phrocs.yml",
    "ci-playwright-container.yml",
    "desktop-agent-release.yml",
    "desktop-release.yml",
    "publish-hogli.yml",
    "publish-owners-yaml.yml",
    "publish-quill-npm.yml",
    "publish-replay-anonymizer-crate.yml",
    "release-cli.yml",
}


class InheritedPublishWorkflowQuarantineTests(unittest.TestCase):
    def test_inventory_is_explicit_and_no_publish_workflow_is_active(self):
        self.assertEqual(MANIFEST["status"], "QUARANTINED_NO_RELEASE_AUTHORIZED")
        self.assertEqual(MANIFEST["count"], 15)
        entries = MANIFEST["workflows"]
        self.assertEqual(len(entries), 15)
        names = set()
        for e in entries:
            source = e["source"]
            target = e["quarantined"]
            name = Path(source).name
            names.add(name)
            with self.subTest(name=name):
                self.assertEqual(source, ".github/workflows/" + name)
                self.assertEqual(
                    target,
                    ".github/quarantined-release-workflows/" + name + ".disabled",
                )
                self.assertFalse((ROOT / source).exists(), source)
                self.assertTrue((ROOT / target).is_file(), target)
                self.assertRegex(e["git_blob_sha1"], r"^[0-9a-f]{40}$")
                self.assertFalse(target.endswith((".yml", ".yaml")))
        self.assertEqual(names, EXPECTED_NAMES)

    def test_parked_workflows_keep_exact_original_git_blob_identity(self):
        for e in MANIFEST["workflows"]:
            with self.subTest(source=e["source"]):
                result = subprocess.run(
                    ["git", "ls-files", "--stage", "--", e["quarantined"]],
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ).stdout
                self.assertIn(e["git_blob_sha1"], result, e["quarantined"])
                self.assertTrue(result.startswith("100644 "))

    def test_no_enabled_workflow_calls_a_quarantined_publisher(self):
        active_workflows = list(ACTIVE.glob("*.yml")) + list(ACTIVE.glob("*.yaml"))
        self.assertGreater(len(active_workflows), 100, "full workflow inventory must be checked")
        for workflow in active_workflows:
            content = workflow.read_text(encoding="utf8")
            for name in EXPECTED_NAMES:
                direct_use = re.compile(
                    r"(?m)^\s*uses:\s*(?:\./)?\.github/workflows/" +
                    re.escape(name) + r"(?:@|\s|$)"
                )
                self.assertNotRegex(content, direct_use, str(workflow))

    def test_new_release_gate_tracks_main_and_quarantine_changes_without_publication(self):
        workflow = (ACTIVE / "flind-release-publish-quarantine.yml").read_text(encoding="utf8")
        self.assertIn("main", workflow)
        self.assertIn("flind-security/quarantine-unqualified-release-workflows-*", workflow)
        self.assertIn("python3 -m unittest tools.flind.test_inherited_release_quarantine", workflow)
        self.assertNotRegex(workflow, r"(?mi)^\s*(?:id-token|packages):\s*write")


if __name__ == "__main__":
    unittest.main()
