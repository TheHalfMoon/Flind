"""Guard independent Flind Mobile OAuth and API destinations without Expo tooling."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "products/desktop/apps/mobile/src/features/auth/lib/constants.ts"
ENV = ROOT / "products/desktop/apps/mobile/.env.example"
TEST = ROOT / "products/desktop/apps/mobile/src/features/auth/lib/constants.test.ts"


class MobileAuthBoundaryWave24Tests(unittest.TestCase):
    def test_no_upstream_cloud_endpoints_or_client_ids_in_runtime(self):
        src = AUTH.read_text()
        self.assertNotIn('return "https://us.post' + 'hog.com"', src)
        self.assertNotIn('return "https://eu.post' + 'hog.com"', src)
        self.assertNotIn('POSTHOG_US_CLIENT_ID', src)
        self.assertNotIn('POSTHOG_EU_CLIENT_ID', src)
        self.assertNotIn('POSTHOG_DEV_CLIENT_ID', src)
        self.assertIn('hostname.endsWith(".posthog.com")', src)

    def test_requires_explicit_flind_env_without_invented_cloud_defaults(self):
        src = AUTH.read_text()
        env = ENV.read_text()
        for key in ('EXPO_PUBLIC_FLIND_API_US_URL', 'EXPO_PUBLIC_FLIND_API_EU_URL',
                    'EXPO_PUBLIC_FLIND_API_DEV_URL', 'EXPO_PUBLIC_FLIND_OAUTH_US_CLIENT_ID',
                    'EXPO_PUBLIC_FLIND_OAUTH_EU_CLIENT_ID', 'EXPO_PUBLIC_FLIND_OAUTH_DEV_CLIENT_ID'):
            with self.subTest(key=key):
                self.assertIn(f'process.env.{key}', src)
                self.assertIn(key + '=', env)

    def test_rejects_insecure_origins_and_dangerous_url_parts(self):
        src = AUTH.read_text()
        for fragment in ('new URL(raw)', 'parsed.protocol !== "https:"',
                         'parsed.username', 'parsed.password', 'parsed.pathname !== "/"',
                         'parsed.search', 'parsed.hash', 'throw new Error'):
            self.assertIn(fragment, src)

    def test_oauth_credentials_cannot_follow_network_redirects(self):
        src = (ROOT / "products/desktop/apps/mobile/src/features/auth/lib/oauth.ts").read_text()
        self.assertEqual(src.count('redirect: "error"'), 2)
        self.assertIn('getCloudUrlFromRegion(config.cloudRegion)', src)
        self.assertIn('getCloudUrlFromRegion(region)', src)

    def test_mobile_user_agent_uses_first_party_brand(self):
        for path in (
            "products/desktop/apps/mobile/src/lib/api.ts",
            "products/desktop/apps/mobile/src/lib/posthogApiClient.ts",
        ):
            source = (ROOT / path).read_text()
            self.assertIn("flind/mobile; version:", source)
            self.assertNotIn("posthog/mobile.hog.dev; version:", source)

    def test_behavioral_vitest_suite_covers_host_and_oauth_fail_closed(self):
        src = TEST.read_text()
        self.assertIn('getCloudUrlFromRegion("us")', src)
        self.assertIn('getOauthClientIdFromRegion("us")', src)
        self.assertIn('"https://us.posthog.com"', src)
        self.assertIn('vi.stubEnv', src)


if __name__ == "__main__":
    unittest.main()
