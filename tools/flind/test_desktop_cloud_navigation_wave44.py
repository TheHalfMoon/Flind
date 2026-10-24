"""Require configured independent Flind app host for outbound Desktop menu URLs."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "products/desktop/packages/ui/src"


class DesktopCloudNavigationWave44Tests(unittest.TestCase):
    def test_cloud_link_is_opt_in_and_hostname_verified(self):
        helper = (UI / "shell/flindExternalLinks.ts").read_text()
        for token in (
            "VITE_FLIND_CLOUD_APP_HOST",
            "VITE_FLIND_CLOUD_APP_URL",
            'verifyFlindExternalLink("website"',
            "destination.origin !== root.origin",
            'root.pathname !== "/"',
            'path.startsWith("//")',
            'path.includes("\\\\")',
        ):
            with self.subTest(token=token):
                self.assertIn(token, helper)

    def test_project_menu_does_not_use_vendor_region_based_links(self):
        menu = (UI / "features/sidebar/components/ProjectSwitcher.tsx").read_text()
        for token in (
            'flindCloudAppPath("/organization/create-project")',
            'flindCloudAppPath("/create-organization")',
            '{createProjectUrl && (',
            '{createOrganizationUrl && (',
            "encodeURIComponent(logoMediaId)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, menu)
        for forbidden in ("getPostHogUrl(", "getCloudUrlFromRegion("):
            self.assertNotIn(forbidden, menu)

    def test_vitest_covers_forged_hosts_and_missing_configuration(self):
        tests = (UI / "shell/flindExternalLinks.test.ts").read_text()
        self.assertIn("independent cloud-app navigation", tests)
        self.assertIn("https://posthog.com", tests)
        self.assertIn("https://app.flind.example.evil.test", tests)
        self.assertIn("https://app.flind.example/", tests)


if __name__ == "__main__":
    unittest.main()
