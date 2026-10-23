"""Regression gates for Flind OAuth defaults, session credentials and API routing."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OAUTH = ROOT / "frontend/src/lib/oauth/oauthClient.ts"


class FlindOAuthIsolationTests(unittest.TestCase):
    def test_no_legacy_cloud_clients_or_hosts_in_oauth_configuration(self) -> None:
        source = OAUTH.read_text()
        self.assertIn("VITE_FLIND_OAUTH_US_CLIENT_ID", source)
        self.assertIn("VITE_FLIND_OAUTH_EU_CLIENT_ID", source)
        self.assertIn("flindOAuthHost(Region.US)", source)
        self.assertIn("flindOAuthHost(Region.EU)", source)
        self.assertNotIn("us.post" + "hog.com", source)
        self.assertNotIn("eu.post" + "hog.com", source)

    def test_stored_session_must_match_approved_origin_and_client(self) -> None:
        source = OAUTH.read_text()
        self.assertIn("const SESSION_KEY = 'flind_oauth_session'", source)
        self.assertIn("isApprovedOAuthTarget(data.backendHost, data.clientId)", source)
        self.assertIn("isApprovedOAuthTarget(pending.backendHost, pending.clientId)", source)
        self.assertIn("!config?.host || !config.clientId", source)

    def test_api_bearer_auth_origin_is_not_string_prefix(self) -> None:
        source = (ROOT / "frontend/src/lib/api.ts").read_text()
        self.assertIn("new URL(url, window.location.origin).origin === session.backendHost", source)
        self.assertNotIn("url.startsWith(session.backendHost)", source)

    def test_localhost_by_default_for_public_apis(self) -> None:
        source = (ROOT / "frontend/src/lib/utils/apiHost.ts").read_text()
        self.assertIn("return window.location.origin", source)
        self.assertNotIn("us.i.post" + "hog.com", source)
        self.assertNotIn("webhooks.us.post" + "hog.com", source)
        self.assertNotIn("live.us.post" + "hog.com", source)

    def test_frontend_and_debug_backend_use_flind_oauth_cookie(self) -> None:
        backend = (ROOT / "posthog/views.py").read_text()
        frontend = OAUTH.read_text()
        self.assertIn('request.COOKIES.get("flind_oauth_mode")', backend)
        self.assertIn("const OAUTH_MODE_COOKIE = 'flind_oauth_mode'", frontend)

    def test_no_buttons_for_unconfigured_remote_region(self) -> None:
        source = (ROOT / "frontend/src/scenes/authentication/shared/authScene/DevLoginPanel.tsx").read_text()
        self.assertIn("configuredOAuthRegion(region) !== null", source)
        source = (ROOT / "frontend/src/lib/oauth/oauthLogic.ts").read_text()
        self.assertIn("const config = configuredOAuthRegion(region)", source)
        self.assertIn("if (!config)", source)


if __name__ == "__main__":
    unittest.main()
