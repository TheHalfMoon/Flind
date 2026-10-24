"""First-party Mobile Studio OAuth/MCP host separation and stale-token gate."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "products/desktop/apps/mobilehog/src"


def read(path: str) -> str:
    return (BASE / path).read_text()


class MobileStudioEgressWave25Tests(unittest.TestCase):
    def test_runtime_has_no_inherited_remote_mcp_or_oauth_defaults(self):
        config = read("config.ts")
        oauth = read("lib/oauth.ts")
        self.assertNotIn('https://mcp.posthog.com', config)
        self.assertNotIn('https://mcp-eu.posthog.com', config)
        self.assertNotIn('https://us.posthog.com', oauth)
        self.assertNotIn('https://eu.posthog.com', oauth)
        self.assertNotIn('CLIENT_IDS', oauth)
        self.assertIn('getFlindStudioApiHost(region)', oauth)
        self.assertIn('getFlindStudioOAuthClientId(region)', oauth)

    def test_explicit_flind_env_and_boundaries(self):
        config = read("config.ts")
        env = (BASE.parent / ".env.example").read_text()
        for key in (
            "EXPO_PUBLIC_FLIND_STUDIO_US_URL", "EXPO_PUBLIC_FLIND_STUDIO_EU_URL",
            "EXPO_PUBLIC_FLIND_STUDIO_MCP_US_URL", "EXPO_PUBLIC_FLIND_STUDIO_MCP_EU_URL",
            "EXPO_PUBLIC_FLIND_STUDIO_OAUTH_US_CLIENT_ID",
            "EXPO_PUBLIC_FLIND_STUDIO_OAUTH_EU_CLIENT_ID",
        ):
            self.assertIn("process.env." + key, config)
            self.assertIn(key + "=", env)
        self.assertIn('host.endsWith(".posthog.com")', config)
        self.assertIn('url.protocol !== "https:"', config)
        self.assertIn('url.username || url.password || url.search || url.hash', config)

    def test_network_clients_do_not_auto_follow_auth_redirects(self):
        mcp = read("lib/mcp/client.ts")
        oauth = read("lib/oauth.ts")
        self.assertIn('new URL(getFlindStudioMcpUrl(session.region))', mcp)
        self.assertIn('redirect: "error"', mcp)
        self.assertIn('redirect: "error"', oauth)
        self.assertIn('getFlindStudioApiHost(region)', oauth)

    def test_stale_session_bearer_cannot_resume_against_old_host(self):
        auth = read("lib/auth.ts")
        self.assertIn('function approvedSessionHost(session: Session)', auth)
        self.assertIn('FLIND_LOCAL_HOST', auth)
        self.assertIn('!approvedSessionHost(session)', auth)
        self.assertIn('!approvedSessionHost(current)', auth)
        self.assertIn('getFlindStudioApiHost(session.region)', auth)
        self.assertIn('Flind session destination is not approved', auth)
        self.assertIn('redirect: "error"', auth)

    def test_behavioral_vitest_cases_exist(self):
        config_tests = read("config.test.ts")
        auth_tests = read("lib/auth.test.ts")
        self.assertIn('getFlindStudioApiHost("us")', config_tests)
        self.assertIn('getFlindStudioMcpUrl("us")', config_tests)
        self.assertIn('getFlindStudioOAuthClientId("us")', config_tests)
        self.assertIn('rejects a legacy cloud host', auth_tests)


if __name__ == "__main__":
    unittest.main()
