"""Shared Flind configuration must not crash without Vite's import.meta.env."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "frontend/src/lib/flindPublicLinks.ts",
    "frontend/src/lib/flindRegionHosts.ts",
    "frontend/src/lib/components/HelpMenu/incidentStatus.ts",
    "frontend/src/scenes/authentication/shared/arrivedFromWebsiteLogic.ts",
    "frontend/src/lib/oauth/oauthClient.ts",
)


class FlindOptionalEnvironmentTests(unittest.TestCase):
    def test_shared_modules_never_dereference_undefined_vite_env(self) -> None:
        for name in FILES:
            with self.subTest(name=name):
                source = (ROOT / name).read_text()
                self.assertNotIn("import.meta.env.VITE_FLIND_", source)
                self.assertIn("import.meta.env?.VITE_FLIND_", source)

    def test_public_links_default_to_unconfigured(self) -> None:
        code = (ROOT / FILES[0]).read_text()
        self.assertIn("VITE_FLIND_WEBSITE_HOST || ''", code)
        self.assertIn("if (\n        !hostname", code)
        self.assertIn("return null", code)

    def test_oauth_client_config_defaults_are_empty(self) -> None:
        code = (ROOT / FILES[4]).read_text()
        for key in ("US", "EU"):
            self.assertIn("import.meta.env?.VITE_FLIND_OAUTH_" + key + "_CLIENT_ID || ''", code)
        self.assertIn("if (!config?.host || !config.clientId", code)

    def test_status_service_remains_optional(self) -> None:
        code = (ROOT / FILES[2]).read_text()
        self.assertIn("import.meta.env?.VITE_FLIND_STATUS_HOST || ''", code)
        self.assertIn("STATUS_PAGE_BASE", code)
        self.assertIn(" : ''", code)


if __name__ == "__main__":
    unittest.main()
