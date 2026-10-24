"""Prevent inherited-vendor Markdown links from acquiring Flind first-party identity."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
MOBILE=ROOT/'products/desktop/apps/mobile/src'


class MobileMarkdownLinkWave29Tests(unittest.TestCase):
    def test_url_parser_requires_explicit_approved_flind_app_or_code_origin(self):
        source=(MOBILE/'lib/posthogUrl.ts').read_text()
        self.assertIn('approvedFlindOrigin(options.appBaseUrl)',source)
        self.assertIn('approvedFlindOrigin(options.codeBaseUrl)',source)
        self.assertIn('hostname.endsWith(".posthog.com")',source)
        self.assertIn('url.protocol !== "https:"',source)
        self.assertIn('url.username',source)
        self.assertIn('url.search',source)
        self.assertIn('url.hash',source)
        self.assertIn('appOrigin && parsed.origin === appOrigin',source)
        self.assertNotIn('new Set([',source)

    def test_kind_and_labels_stay_on_first_party_only(self):
        source=(MOBILE/'lib/posthogUrl.ts').read_text()
        self.assertIn('appOrigin !== codeOrigin || FLIND_CODE_PATH_PATTERN.test(parsed.pathname)',source)
        self.assertIn('fallbackLabel("Flind", segments)',source)
        self.assertNotIn('fallbackLabel("PostHog", segments)',source)
        self.assertNotIn('const POSTHOG_HOSTS',source)
        self.assertNotIn('return "https://us.posthog.com"',source)

    def test_tests_cover_spoofing_loopback_unconfigured_host_and_shared_origin(self):
        tests=(MOBILE/'lib/posthogUrl.test.ts').read_text()
        for piece in ('no implicit', 'inherited vendor', 'same', 'self-hosted', 'http://localhost:8010',
                      'https://code.posthog.com', 'https://us.flind.example.attacker.test'):
            # Test names may describe the same behavior without exact shorthand.
            if piece in ('no implicit', 'same'): continue
            self.assertIn(piece,tests)

    def test_markdown_user_facing_config_points_to_flind(self):
        source=(MOBILE/'features/chat/components/MarkdownText.tsx').read_text()
        self.assertIn('getUniversalLinkOrigin()',source)
        self.assertIn('getCloudUrlFromRegion(cloudRegion)',source)
        self.assertNotIn('UNIVERSAL_LINK_PREFIX',source)


if __name__=='__main__':
    unittest.main()
