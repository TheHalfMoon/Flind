"""Mobile native identity and deep link safety independent of Expo runtime."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[2]
MOBILE=ROOT/'products/desktop/apps/mobile'


class MobileNativeIdentityWave28Tests(unittest.TestCase):
    def test_ios_android_provisional_first_party_identity_and_no_inherited_eas_project(self):
        expo=json.loads((MOBILE/'app.json').read_text())['expo']
        self.assertEqual(expo['name'],'Flind')
        self.assertEqual(expo['slug'],'flind')
        self.assertEqual(expo['scheme'],'flind')
        self.assertEqual(expo['ios']['bundleIdentifier'],'com.thehalfmoon.flind.mobile')
        self.assertEqual(expo['android']['package'],'com.thehalfmoon.flind.mobile')
        self.assertNotIn('owner',expo)
        self.assertNotIn('eas',expo['extra'])
        self.assertNotIn('LSApplicationQueriesSchemes',expo['ios']['infoPlist'])

    def test_unverified_universal_link_claims_not_registered(self):
        expo=json.loads((MOBILE/'app.json').read_text())['expo']
        self.assertEqual(expo['ios']['associatedDomains'],[])
        self.assertEqual(expo['android']['intentFilters'],[])

    def test_explicit_https_link_builder_and_matching_receiver(self):
        s=(MOBILE/'src/lib/deep-links.ts').read_text()
        self.assertIn('MOBILE_SCHEME = "flind"',s)
        self.assertIn('EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN',s)
        self.assertIn('hostname.endsWith(".posthog.com")',s)
        self.assertIn('parsed.protocol === "https:"',s)
        self.assertIn('getUniversalLinkOrigin() !== null',s)
        self.assertIn('Flind universal links are not configured',s)
        self.assertNotIn('UNIVERSAL_LINK_HOST',s)
        self.assertNotIn('UNIVERSAL_LINK_PREFIX',s)

    def test_oauth_callbacks_follow_new_native_scheme(self):
        auth=(MOBILE/'src/features/auth/lib/oauth.ts').read_text()
        mcp=(MOBILE/'src/features/mcp/oauth.ts').read_text()
        github=(MOBILE/'src/features/tasks/components/GitHubConnectionPrompt.tsx').read_text()
        self.assertIn('scheme: "flind"',auth)
        self.assertIn('"flind://mcp-oauth/callback"',mcp)
        self.assertIn('"flind://github/callback"',github)
        self.assertNotIn('posthog://',mcp)
        self.assertNotIn('posthog://',github)

    def test_not_inventing_a_live_domain_or_telemetry(self):
        env=(MOBILE/'.env.example').read_text()
        self.assertIn('EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN=',env)
        self.assertIn('getUniversalLinkOrigin()', (MOBILE/'src/features/chat/components/MarkdownText.tsx').read_text())


if __name__=='__main__':
    unittest.main()
