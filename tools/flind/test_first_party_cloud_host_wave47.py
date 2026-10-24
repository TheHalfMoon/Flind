"""Qualify central hosted Cloud and OAuth identities as opt-in, not donor defaults."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages/agent/packages/agent-contracts/src"


class FirstPartyCloudHostWave47Tests(unittest.TestCase):
    def test_all_hosted_regions_call_the_shared_verified_configuration(self):
        source = (CONTRACTS / "urls.ts").read_text()
        self.assertIn("configuredFlindHostedCloud(region).url", source)
        for token in ('return "https://us.', 'return "https://eu.', 'return "https://app.dev.'):
            self.assertNotIn(token, source)
        self.assertIn('return "http://localhost:8010"', source)

    def test_production_oauth_does_not_return_inherited_registered_ids(self):
        source = (CONTRACTS / "oauth.ts").read_text()
        start = source.index("export function getOauthClientIdFromRegion(")
        fn = source[start:]
        self.assertIn("configuredFlindHostedCloud(region).oauthClientId", fn)
        for token in ("return POSTHOG_US_CLIENT_ID", "return POSTHOG_EU_CLIENT_ID",
                      "return POSTHOG_DEV_CLOUD_CLIENT_ID"):
            self.assertNotIn(token, fn)

    def test_hosted_cloud_requires_verified_url_and_registered_client_pair(self):
        source = (CONTRACTS / "flind-hosted-cloud.ts").read_text()
        for name in ("FLIND_US_CLOUD_URL", "FLIND_EU_CLOUD_URL", "FLIND_DEV_CLOUD_URL",
                     "FLIND_US_OAUTH_CLIENT_ID", "FLIND_EU_OAUTH_CLIENT_ID",
                     "FLIND_DEV_CLOUD_OAUTH_CLIENT_ID"):
            self.assertIn(name, source)
        self.assertIn("normalizeCustomCloud(", source)
        self.assertIn('throw new Error(', source)

    def test_cloud_url_normalization_rejects_embedded_credentials(self):
        source = (CONTRACTS / "custom-cloud.ts").read_text()
        self.assertIn("parsed.username || parsed.password", source)
        tests = (CONTRACTS / "custom-cloud.test.ts").read_text()
        self.assertIn("embedded username", tests)
        self.assertIn("embedded password", tests)

    def test_real_browser_oauth_tests_enforce_no_network_without_flind_config(self):
        source = (ROOT / "products/desktop/apps/web/src/web-oauth-flow.test.ts").read_text()
        self.assertIn("fetcher).not.toHaveBeenCalled()", source)
        self.assertIn("https://us.flind.example/oauth/token", source)
        self.assertIn("flind-published-client-id", source)


if __name__ == "__main__":
    unittest.main()
