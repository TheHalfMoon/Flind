"""Protect published UI dependencies against cosmetic, nonexistent registry renaming."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "products/desktop"


class UiPublishedAliasWave40Tests(unittest.TestCase):
    def test_external_quill_alias_in_workspace_catalog(self):
        config = (DESKTOP / "pnpm-workspace.yaml").read_text()
        self.assertIn(
            "'@flind/quill': npm:@posthog/quill@0.3.0-beta.29", config
        )
        self.assertIn(
            "'@posthog/quill>@base-ui/react': ^1.3.0", config
        )

    def test_external_charts_alias_in_ui_manifest(self):
        package = json.loads((DESKTOP / "packages/ui/package.json").read_text())
        self.assertEqual(
            package["dependencies"]["@flind/quill-charts"],
            "npm:@posthog/quill-charts@0.3.0-beta.29",
        )
        for section in ("peerDependencies", "devDependencies"):
            self.assertEqual(package[section]["@flind/quill"], "catalog:")

    def test_lock_references_actual_published_artifacts_and_integrities(self):
        lock = (DESKTOP / "pnpm-lock.yaml").read_text()
        self.assertIn(
            "'@posthog/quill@0.3.0-beta.29':\n"
            "    resolution: {integrity: sha512-ZKMlqqyNSchwgoVVpk2TrhANTWJqOJTY8xbdQRwC5XuhqqY1QQOmstJInMZhh0S1AEqc/qnG+H7KxDog5vJUCw==}",
            lock,
        )
        self.assertIn(
            "'@posthog/quill-charts@0.3.0-beta.29':\n"
            "    resolution: {integrity: sha512-zuIP2dgt8hPOFmINAsueBMMnTEOlB5CXqWwqJBAWFM9cYlxIhd3IUZqRfwUC1Ockr/Yw0EqKwZwBAa7rLzdxvw==}",
            lock,
        )
        self.assertNotIn("'@flind/quill@0.3.0-beta.29':", lock)
        self.assertNotIn("'@flind/quill-charts@0.3.0-beta.29':", lock)


if __name__ == "__main__":
    unittest.main()
