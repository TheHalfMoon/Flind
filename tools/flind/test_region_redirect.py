"""Dependency-free regression tests for opt-in, first-party Flind redirects."""
from __future__ import annotations

import unittest
from pathlib import Path

from flind.region_redirect import allowed_region_host, valid_region_hostname

ROOT = Path(__file__).resolve().parents[2]
REGIONS = ("us.flind.example", "eu.flind.example")


class FlindRegionRedirectTests(unittest.TestCase):
    def test_no_config_never_authorizes_redirect(self) -> None:
        self.assertIsNone(allowed_region_host("https://us.flind.example", ()))

    def test_only_operator_allowlisted_region_can_redirect(self) -> None:
        self.assertEqual(allowed_region_host("https://eu.flind.example", REGIONS), "eu.flind.example")
        self.assertEqual(allowed_region_host('"https://us.flind.example"', REGIONS), "us.flind.example")

    def test_untrusted_cookie_hosts_are_rejected(self) -> None:
        hostile = [
            "https://unknown.example.com",
            "https://us.flind.example@evil.example.com",
            "https://evil.example.com@us.flind.example",
            "http://us.flind.example",
            "javascript:alert(1)",
            "https://us.flind.example:8000",
            "https://us.flind.example/path",
            "https://us.flind.example/?next=evil",
            "https://us.flind.example/#fragment",
            "https://us.flind.example%00.evil.example.com",
            "//us.flind.example",
            "yo ho ho",
            "",
            None,
        ]
        for cookie in hostile:
            with self.subTest(cookie=cookie):
                self.assertIsNone(allowed_region_host(cookie, REGIONS))

    def test_invalid_configured_hostname_cannot_be_trusted(self) -> None:
        for host in ["", "https://us.flind.example", "UPPER.EXAMPLE.COM", "a..b", "-bad.example", "bad-.example", "us.flind.example/path", "a@b.com"]:
            with self.subTest(host=host):
                self.assertIsNone(valid_region_hostname(host))
        self.assertEqual(valid_region_hostname("us.flind.example"), "us.flind.example")

    def test_app_host_defaults_do_not_point_outside_flind(self) -> None:
        settings = (ROOT / "posthog/settings/web.py").read_text()
        backend = (ROOT / "posthog/frontend_views.py").read_text()
        for env in ("FLIND_APP_HOST", "FLIND_REGION_HOST_US", "FLIND_REGION_HOST_EU"):
            self.assertIn(f'os.getenv("{env}", "")', settings)
        self.assertIn('get_from_env("FLIND_REDIRECT_TO_PRIMARY", False, type_cast=str_to_bool)', settings)
        self.assertIn("settings.FLIND_REDIRECT_TO_PRIMARY", backend)
        self.assertIn("allowed_region_host(", backend)
        self.assertIn('app_host = valid_region_hostname(settings.FLIND_APP_HOST)', backend)
        self.assertNotIn("app.post" + "hog.com", backend)
        self.assertNotIn("us.post" + "hog.com", backend)
        self.assertNotIn("eu.post" + "hog.com", backend)

    def test_unsafe_client_side_redirect_removed(self) -> None:
        unsafe = ROOT / "frontend/src/scenes/authentication/shared/RedirectToLoggedInInstance.tsx"
        self.assertFalse(unsafe.exists())

    def test_login_has_no_dangling_import_of_removed_redirect(self) -> None:
        login = (ROOT / "frontend/src/scenes/authentication/login/LoginForm.tsx").read_text()
        self.assertNotIn("RedirectToLoggedInInstance", login)
        self.assertNotIn("RedirectIfLoggedInOtherInstance", login)


if __name__ == "__main__":
    unittest.main()
