"""Flind-owned status-page polling and visible-link boundary."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "frontend/src/lib/components/HelpMenu"
LEGACY = "post" + "hogstatus.com"


class FlindStatusFeedTests(unittest.TestCase):
    def test_no_old_status_feed_origin_is_embedded(self) -> None:
        for rel in ("incidentStatus.ts", "incidentStatusLogic.tsx"):
            with self.subTest(file=rel):
                self.assertNotIn(LEGACY, (BASE / rel).read_text())

    def test_flind_status_requires_operator_hostname(self) -> None:
        source = (BASE / "incidentStatus.ts").read_text()
        self.assertIn("VITE_FLIND_STATUS_HOST", source)
        self.assertIn("configuredStatusPageHost()", source)
        self.assertIn(" : ''", source)

    def test_no_backend_status_fetch_without_configured_host(self) -> None:
        source = (BASE / "incidentStatusLogic.tsx").read_text()
        self.assertIn("if (!STATUS_PAGE_BASE || !values.relevantGroupName)", source)
        self.assertIn("flindRegionHost(region)", source)
        self.assertNotIn("'us.post" + "hog.com'", source)

    def test_no_unconfigured_outbound_status_navigation(self) -> None:
        for rel in (
            "frontend/src/lib/components/HelpMenu/HelpMenu.tsx",
            "frontend/src/layout/today/TodayMoreMenu.tsx",
            "frontend/src/layout/today/TodaySupportStatusAlert.tsx",
            "frontend/src/layout/navigation-3000/sidepanel/panels/support/SidePanelSupport.tsx",
        ):
            with self.subTest(file=rel):
                source = (ROOT / rel).read_text()
                self.assertIn("statusPageUrl", source)
                self.assertTrue(
                    "statusPageUrl &&" in source or "statusPageUrl ?" in source
                )

    def test_status_unit_tests_expect_no_unconfigured_provider_egress(self) -> None:
        source = (BASE / "incidentStatusLogic.test.ts").read_text()
        self.assertIn("no external status source", source)
        self.assertIn("STATUS_PAGE_BASE &&", source)


if __name__ == "__main__":
    unittest.main()
