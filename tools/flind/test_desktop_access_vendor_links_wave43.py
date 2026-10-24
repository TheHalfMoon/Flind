"""Desktop access restriction UI must not link to old vendor marketing."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
ACCESS=ROOT/"products/desktop/packages/ui/src/features/auth/components/DesktopAccessScreen.tsx"
TEST=ROOT/"products/desktop/packages/ui/src/features/auth/components/DesktopAccessScreen.test.tsx"


class DesktopAccessVendorLinksWave43Tests(unittest.TestCase):
    def test_legacy_marketing_and_games_removed_from_access_ui(self):
        source=ACCESS.read_text()
        for forbidden in (
            "POSTHOG_GAMES_URL", "openGames()", "openExternalUrl(",
            "posthog.com", "sales@posthog", "GameController", "PostHog Desktop",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden,source)

    def test_backend_policy_reasons_keep_local_recovery(self):
        source=ACCESS.read_text()
        for token in ("startup_plan:", "prepaid_credits:", "SIGNUPS_PAUSED_CONTENT",
                      "onSelectOrganization(value.id)", "onSelectProject(value.id)",
                      "onRetry", "onLogout", "FullScreenLayout"):
            with self.subTest(token=token):
                self.assertIn(token,source)

    def test_browser_tests_check_no_vendor_actions(self):
        source=TEST.read_text()
        self.assertIn('container.querySelector(',source)
        self.assertIn('not.toContain("PostHog")',source)
        self.assertIn('not.toContain("sales@")',source)
        self.assertNotIn('openExternalUrl',source)


if __name__ == "__main__":
    unittest.main()
