"""Wave 68: prohibit a valid API key from waiving browser-session CSRF."""
import unittest

from tools.flind.test_csrf_personal_key_wave66 import (
    REFUSED,
    FakePersonalAPIKeyAuthentication as Auth,
    FakeRequest,
    load_actual_class,
)


class CsrfCookieWave68Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.middle = load_actual_class()

    def setUp(self):
        Auth.candidate = None
        Auth.validated = False
        Auth.failure = None
        Auth.lookup_calls = 0
        Auth.validation_calls = 0
        self.middleware = self.middle(lambda request: None)

    def attempt(self, request):
        return self.middleware.process_view(request, lambda req: None, (), {})

    def test_valid_attacker_key_can_never_waive_victim_session_csrf(self):
        Auth.validated = True
        for source in ("header", "body", "query_string"):
            with self.subTest(source=source):
                Auth.candidate = ("synthetic-attacker-owned-valid-key", source)
                victim = FakeRequest()
                victim.COOKIES["sessionid"] = "victim-session"
                self.assertIs(self.attempt(victim), REFUSED)
                self.assertFalse(victim.csrf_processing_done)
        self.assertEqual(Auth.validation_calls, 0)
        self.assertEqual(Auth.lookup_calls, 0)

    def test_empty_or_null_cookie_remains_a_cookie_boundary(self):
        Auth.candidate = ("attacker-key", "header")
        Auth.validated = True
        for raw in ("", None, "fake", "expired"):
            with self.subTest(raw=raw):
                request = FakeRequest()
                request.COOKIES["sessionid"] = raw
                self.assertIs(self.attempt(request), REFUSED)
        self.assertEqual(Auth.lookup_calls, 0)

    def test_cookie_free_personal_api_clients_still_work(self):
        Auth.validated = True
        for source in ("header", "body", "query_string"):
            with self.subTest(source=source):
                Auth.candidate = ("valid-key", source)
                request = FakeRequest()
                self.assertIsNone(self.attempt(request))
                self.assertTrue(request.csrf_processing_done)
        self.assertEqual(Auth.validation_calls, 3)

    def test_other_cookies_are_not_session_cookie(self):
        Auth.candidate = ("valid-key", "header")
        Auth.validated = True
        request = FakeRequest()
        request.COOKIES["analytics_optout"] = "1"
        self.assertIsNone(self.attempt(request))
        self.assertTrue(request.csrf_processing_done)

    def test_csrf_valid_browser_with_cookie_is_unchanged(self):
        request = FakeRequest(valid_csrf=True)
        request.COOKIES["sessionid"] = "real-session"
        self.assertIsNone(self.attempt(request))
        self.assertEqual(Auth.lookup_calls, 0)

    def test_custom_session_cookie_name_is_honored(self):
        settings = self.middle.process_view.__globals__["settings"]
        original = settings.SESSION_COOKIE_NAME
        try:
            settings.SESSION_COOKIE_NAME = "flind_session"
            Auth.candidate = ("valid-key", "query_string")
            Auth.validated = True
            request = FakeRequest()
            request.COOKIES["flind_session"] = "victim"
            self.assertIs(self.attempt(request), REFUSED)
            self.assertEqual(Auth.validation_calls, 0)
        finally:
            settings.SESSION_COOKIE_NAME = original

    def test_bad_key_is_rejected_without_cookie_as_before(self):
        request = FakeRequest()
        Auth.candidate = ("forged", "header")
        self.assertIs(self.attempt(request), REFUSED)
        self.assertEqual(Auth.validation_calls, 1)


if __name__ == "__main__":
    unittest.main()
