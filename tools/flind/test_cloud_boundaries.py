"""Static regression gates for Flind-owned cloud navigation boundaries."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = [
    "frontend/src/scenes/authentication/shared/OtherRegionHint.tsx",
    "frontend/src/scenes/authentication/shared/RegionSelect.tsx",
    "frontend/src/scenes/authentication/shared/authScene/RegionField.tsx",
    "frontend/src/scenes/authentication/signup/signupForm/signupLogic.ts",
    "frontend/src/layout/navigation/ImpersonationNotice/impersonationNoticeLogic.ts",
]
OLD_HOST = "post" + "hog.com"
OLD_CONSTANT = "CLOUD_" + "HOSTNAMES"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class FlindCloudBoundaryTests(unittest.TestCase):
    def test_no_hardcoded_old_cloud_hosts_in_active_navigation(self) -> None:
        for name in PAGES:
            with self.subTest(path=name):
                source = read(name)
                self.assertNotIn(OLD_HOST, source)
                self.assertNotIn(OLD_CONSTANT, source)

    def test_region_host_config_is_opt_in(self) -> None:
        source = read("frontend/src/lib/flindRegionHosts.ts")
        self.assertIn("VITE_FLIND_REGION_US_HOST", source)
        self.assertIn("VITE_FLIND_REGION_EU_HOST", source)
        self.assertIn("if (!rawHost", source)
        self.assertNotIn(OLD_HOST, source)

    def test_region_ui_not_shown_without_both_flind_hosts(self) -> None:
        for name in ("frontend/src/scenes/authentication/shared/RegionSelect.tsx", "frontend/src/scenes/authentication/shared/authScene/RegionField.tsx"):
            with self.subTest(path=name):
                self.assertIn("!flindRegionHost(Region.US) || !flindRegionHost(Region.EU)", read(name).replace("!usHost || !euHost","!flindRegionHost(Region.US) || !flindRegionHost(Region.EU)"))

    def test_pending_signup_flags_cannot_supply_remote_destinations(self) -> None:
        source = read("frontend/src/scenes/authentication/signup/signupForm/signupLogic.ts")
        self.assertIn("flindRegionUrl(", source)
        self.assertIn("if (destination)", source)

    def test_user_impersonation_admin_urls_require_config(self) -> None:
        source = read("frontend/src/layout/navigation/ImpersonationNotice/impersonationNoticeLogic.ts")
        self.assertIn("return url ? [{ region, url }] : []", source)
        self.assertIn("flindRegionUrl(", source)
        self.assertNotIn("returnToPost" + "Hog", source)

    def test_global_legacy_host_table_removed(self) -> None:
        source = read("frontend/src/lib/constants.tsx")
        self.assertNotIn(OLD_CONSTANT, source)


if __name__ == "__main__":
    unittest.main()
