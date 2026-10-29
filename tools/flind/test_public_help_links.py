"""Flind first-party public help link regression boundary."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "frontend/src/lib/components/HelpMenu/HelpMenu.tsx",
    "frontend/src/layout/scenes/components/SceneMenuBar.tsx",
    "frontend/src/layout/today/TodayMoreMenu.tsx",
    "frontend/src/layout/today/TodaySupportPanel.tsx",
    "frontend/src/layout/navigation-3000/sidepanel/panels/support/SidePanelSupport.tsx",
)
VENDOR = "post" + "hog.com"


class FlindPublicHelpTests(unittest.TestCase):
    def test_all_primary_help_surfaces_no_longer_link_to_unowned_vendor_site(self) -> None:
        for filename in FILES:
            with self.subTest(file=filename):
                source = (ROOT / filename).read_text(encoding="utf-8")
                self.assertNotIn("https://" + VENDOR, source)
                self.assertIn("flindPublicUrl", source)

    def test_unconfigured_help_pages_do_not_show_broken_buttons(self) -> None:
        for filename in FILES:
            with self.subTest(file=filename):
                source = (ROOT / filename).read_text(encoding="utf-8")
                self.assertTrue(
                    "docsUrl &&" in source
                    or "changelogUrl &&" in source
                    or "communityUrl &&" in source
                    or "roadmapUrl &&" in source
                    or "feedbackUrl &&" in source
                )

    def test_only_operator_configured_exact_first_party_site_is_trusted(self) -> None:
        source = (ROOT / "frontend/src/lib/flindPublicLinks.ts").read_text(encoding="utf-8")
        self.assertIn("VITE_FLIND_WEBSITE_HOST", source)
        self.assertIn("VITE_FLIND_DOCS_URL", source)
        self.assertIn("VITE_FLIND_CHANGELOG_URL", source)
        self.assertIn("VITE_FLIND_COMMUNITY_URL", source)
        self.assertIn("VITE_FLIND_ROADMAP_URL", source)
        self.assertIn("url.hostname !== hostname", source)
        self.assertIn("url.protocol !== 'https:'", source)
        self.assertNotIn("https://" + VENDOR, source)

    def test_cloud_upgrade_link_is_not_shown_to_flind_local_users(self) -> None:
        source = (ROOT / "frontend/src/lib/components/HelpMenu/HelpMenu.tsx").read_text(encoding="utf-8")
        self.assertNotIn("Try Post" + "Hog Cloud", source)
        self.assertNotIn("moveToPost" + "HogCloud", source)

    def test_help_link_tests_include_hostile_destinations(self) -> None:
        source = (ROOT / "frontend/src/lib/flindPublicLinks.test.ts").read_text(encoding="utf-8")
        self.assertIn(VENDOR + "/docs", source)
        self.assertIn("www.flind.example.attacker.com", source)
        self.assertIn(":8443/docs", source)
        self.assertIn("javascript:alert(1)", source)


if __name__ == "__main__":
    unittest.main()
