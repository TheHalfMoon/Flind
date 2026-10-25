"""CSRF must not be bypassed by merely presenting an unverified API key.

Compile the actual middleware class source so the regression suite remains
runnable without the heavyweight Django/PostgreSQL dependency lock.
"""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "posthog/middleware.py"
REFUSED = object()


class FakeAuthenticationFailed(Exception):
    pass


class FakeCsrfViewMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_view(self, request, callback, callback_args, callback_kwargs):
        return None if getattr(request, "valid_csrf", False) else REFUSED


class FakePersonalAPIKeyAuthentication:
    candidate = None
    validated = False
    failure = None
    lookup_calls = 0
    validation_calls = 0

    @classmethod
    def find_key_with_source(cls, request):
        cls.lookup_calls += 1
        return cls.candidate

    @classmethod
    def validate_key(cls, candidate):
        cls.validation_calls += 1
        if cls.failure:
            raise cls.failure
        if not cls.validated:
            raise FakeAuthenticationFailed("Invalid personal API key")
        return object()


def load_actual_class():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    nodes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "CsrfOrKeyViewMiddleware"
    ]
    if len(nodes) != 1:
        raise AssertionError("Expected one CsrfOrKeyViewMiddleware in real source")
    source = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace = {
        "CsrfViewMiddleware": FakeCsrfViewMiddleware,
        "PersonalAPIKeyAuthentication": FakePersonalAPIKeyAuthentication,
        "AuthenticationFailed": FakeAuthenticationFailed,
    }
    exec(compile(source, str(SOURCE), "exec"), namespace)
    return namespace["CsrfOrKeyViewMiddleware"]


class FakeRequest:
    def __init__(self, valid_csrf=False):
        self.valid_csrf = valid_csrf
        self.csrf_processing_done = False


class CsrfPersonalKeyWave66Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.middle = load_actual_class()

    def setUp(self):
        a = FakePersonalAPIKeyAuthentication
        a.candidate = None
        a.validated = False
        a.failure = None
        a.lookup_calls = 0
        a.validation_calls = 0
        self.middleware = self.middle(lambda request: None)

    def attempt(self, request):
        return self.middleware.process_view(request, lambda request: None, (), {})

    def test_valid_csrf_still_allowed_without_api_key_lookup(self):
        self.assertIsNone(self.attempt(FakeRequest(valid_csrf=True)))
        self.assertEqual(FakePersonalAPIKeyAuthentication.lookup_calls, 0)

    def test_absent_api_key_does_not_bypass_failed_csrf(self):
        self.assertIs(self.attempt(FakeRequest()), REFUSED)
        self.assertEqual(FakePersonalAPIKeyAuthentication.validation_calls, 0)

    def test_any_fake_api_key_still_rejected(self):
        a = FakePersonalAPIKeyAuthentication
        for source in ("header", "body", "query_string"):
            with self.subTest(source=source):
                a.candidate = ("fake-user-supplied-token", source)
                a.validated = False
                a.failure = None
                self.assertIs(self.attempt(FakeRequest()), REFUSED)
        self.assertEqual(a.validation_calls, 3)

    def test_expired_or_revoked_keys_are_not_csrf_substitutes(self):
        a = FakePersonalAPIKeyAuthentication
        a.candidate = ("expired-token", "header")
        a.failure = FakeAuthenticationFailed("Expired or revoked")
        self.assertIs(self.attempt(FakeRequest()), REFUSED)

    def test_real_valid_personal_key_can_still_access_key_authenticated_api(self):
        a = FakePersonalAPIKeyAuthentication
        a.candidate = ("valid-token", "header")
        a.validated = True
        request = FakeRequest()
        self.assertIsNone(self.attempt(request))
        self.assertTrue(request.csrf_processing_done)
        self.assertEqual(a.validation_calls, 1)

    def test_empty_oversized_or_nonstring_key_does_not_trigger_db_hashing(self):
        a = FakePersonalAPIKeyAuthentication
        for token in ("", "x" * 1025, False, None, {"token": "x"}, []):
            with self.subTest(type=type(token).__name__):
                a.candidate = (token, "query_string")
                a.validated = True
                self.assertIs(self.attempt(FakeRequest()), REFUSED)
        self.assertEqual(a.validation_calls, 0)

    def test_database_failures_are_not_silently_accepted(self):
        a = FakePersonalAPIKeyAuthentication
        a.candidate = ("valid-looking-token", "header")
        a.failure = RuntimeError("Database unavailable")
        with self.assertRaisesRegex(RuntimeError, "Database unavailable"):
            self.attempt(FakeRequest())

    def test_middleware_source_has_no_presence_only_accept_path(self):
        text = SOURCE.read_text(encoding="utf-8")
        body = text.split("class CsrfOrKeyViewMiddleware", 1)[1].split(
            "\n\n# Work around", 1
        )[0]
        self.assertIn("PersonalAPIKeyAuthentication.validate_key(candidate)", body)
        self.assertIn("except AuthenticationFailed:", body)
        self.assertNotIn(
            "find_key_with_source(request) is not None",
            body,
        )


if __name__ == "__main__":
    unittest.main()
