"""Protect UI navigation against arbitrary absolute and inherited region URLs."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "products/desktop/packages/ui/src"


class DesktopProjectLinkWave46Tests(unittest.TestCase):
    def test_navigation_never_uses_inherited_region_host(self):
        source = (UI / "utils/urls.ts").read_text()
        func = source[source.index("export function getPostHogUrl("):
                      source.index("/** A Flind payment URL")]
        for forbidden in (
            "getCloudUrlFromRegion(",
            "return pathOrUrl",
            "useAuthStore.getState()",
            "posthog.com",
        ):
            self.assertNotIn(forbidden, func)
        for token in (
            'flindCloudAppPath("/")',
            "verifyFlindExternalLink(",
            "new URL(verified).origin === new URL(root).origin",
            "return flindCloudAppPath(",
        ):
            self.assertIn(token, func)

    def test_native_vitest_covers_both_internal_and_absolute_navigation(self):
        tests = (UI / "utils/urls.test.ts").read_text()
        for token in (
            "first-party-only project navigation",
            "refuses region-derived inherited hosts",
            "allows verified absolute Flind app URLs",
            "https://app.flind.example.evil.test/foo",
            "javascript:alert(1)",
        ):
            self.assertIn(token, tests)


if __name__ == "__main__":
    unittest.main()
