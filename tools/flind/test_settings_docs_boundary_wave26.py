"""Prevent inherited documentation hosts from returning to active Flind settings."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "frontend/src/scenes/settings/SettingsMap.tsx"
SETTINGS = ROOT / "frontend/src/scenes/settings/Settings.tsx"
TYPES = ROOT / "frontend/src/scenes/settings/types.ts"


class SettingsDocsBoundaryWave26Tests(unittest.TestCase):
    def test_settings_map_does_not_advertise_inherited_vendor_docs(self):
        source = MAP.read_text()
        upstream = re.compile(r"docsUrl:\s*['\"]https?://(?:www\.)?posthog\.com/")
        self.assertNotRegex(source, upstream)
        self.assertNotIn("Install PostHog in your app", source)
        self.assertIn("Install Flind in your app", source)

    def test_legitimate_third_party_provider_docs_preserved(self):
        source = MAP.read_text()
        for actual in ("docsUrl: Slack.docsUrl", "docsUrl: GitHub.docsUrl", "docsUrl: Linear.docsUrl"):
            with self.subTest(actual=actual):
                self.assertIn(actual, source)

    def test_frontend_hides_missing_help_links_without_inventing_destinations(self):
        settings = SETTINGS.read_text()
        types = TYPES.read_text()
        self.assertIn("x.docsUrl &&", settings)
        self.assertIn("to={x.docsUrl}", settings)
        self.assertIn("docsUrl?: string", types)


if __name__ == "__main__":
    unittest.main()
