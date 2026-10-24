"""Mobile Studio native app identity, OTA safety, and notification navigation."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'products/desktop/apps/mobilehog'


class MobileStudioNativeIdentityWave30Tests(unittest.TestCase):
    def test_native_app_is_not_bound_to_inherited_eas_account(self):
        expo=json.loads((BASE/'app.json').read_text())['expo']
        self.assertEqual(expo['name'],'Flind Studio')
        self.assertEqual(expo['slug'],'flind-studio')
        self.assertEqual(expo['scheme'],'flind-studio')
        self.assertEqual(expo['ios']['bundleIdentifier'],'com.thehalfmoon.flind.studio')
        self.assertEqual(expo['android']['package'],'com.thehalfmoon.flind.studio')
        self.assertNotIn('owner',expo)
        self.assertNotIn('eas',expo['extra'])

    def test_inherited_over_the_air_update_channel_is_disabled(self):
        expo=json.loads((BASE/'app.json').read_text())['expo']
        self.assertFalse(expo['updates']['enabled'])
        self.assertNotIn('url',expo['updates'])
        self.assertNotIn('NSAllowsArbitraryLoads',expo['ios']['infoPlist']['NSAppTransportSecurity'])
        self.assertTrue(expo['ios']['infoPlist']['NSAppTransportSecurity']['NSAllowsLocalNetworking'])

    def test_oauth_redirect_uses_native_first_party_scheme(self):
        oauth=(BASE/'src/lib/oauth.ts').read_text()
        self.assertIn('scheme: "flind-studio"',oauth)
        self.assertNotIn('scheme: "posthog"',oauth)
        for path in ('src/lib/api.ts','src/lib/client.ts'):
            source=(BASE/path).read_text()
            self.assertIn('flind/mobile-studio; version:',source)
            self.assertNotIn('posthog/mobilehog; version:',source)

    def test_push_navigation_accepts_only_flind_studio_routes(self):
        paths=(BASE/'src/lib/notificationPaths.ts').read_text()
        self.assertIn('uri.protocol !== "flind-studio:"',paths)
        self.assertIn('["task", "report"].includes(uri.hostname)',paths)
        self.assertIn('notificationTaskIdToPath',paths)
        notify=(BASE/'src/lib/notifications.ts').read_text()
        self.assertIn('notificationUrlToAppPath(data.url)',notify)
        self.assertIn('notificationTaskIdToPath(data.taskId)',notify)
        self.assertNotIn('data.url.replace(',notify)

    def test_vitest_behavioral_cases_present(self):
        tests=(BASE/'src/lib/notificationPaths.test.ts').read_text()
        for marker in ('posthog://task','flind-studio://task','https://example.com','../settings'):
            self.assertIn(marker,tests)


if __name__=='__main__':
    unittest.main()
