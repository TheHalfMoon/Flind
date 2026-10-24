"""Execute real Flind forum SSO endpoints without Django/network dependencies.

The source functions are compiled from AST with injected dependencies:
unexpected network or redirect actions fail the behavioral test. These
checks do NOT replace full Django integration/authorization tests.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse, urlencode
import unittest

ROOT = Path(__file__).resolve().parents[2]
USER_SOURCE = ROOT / "posthog/api/user.py"
TOOLBAR_SOURCE = ROOT / "posthog/api/oauth/toolbar_views.py"
FORUM_TEMPLATE = ROOT / "posthog/templates/authorize_and_link.html"


def real_function(source: Path, name: str, namespace: dict):
    parsed = ast.parse(source.read_text())
    function = next(
        node for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    function.decorator_list = []
    compiled = compile(
        ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
        str(source),
        "exec",
    )
    exec(compiled, namespace)
    return namespace[name]


class NoNetwork:
    def request(self, *args, **kwargs):
        raise AssertionError("Unexpected inherited forum outbound registration")


def reject_redirect(*args, **kwargs):
    raise AssertionError("Unexpected redirect to an inherited provider")


def make_response(message="", *, status=200):
    return SimpleNamespace(body=message, status_code=status)


class TrapUser:
    def __getattribute__(self, name):
        raise AssertionError("Forum route must not access user field " + name)


class ForumSsoEgressWave38Tests(unittest.TestCase):
    def test_authenticated_legacy_forum_route_refuses_without_pii_or_network(self):
        func = real_function(
            USER_SOURCE,
            "redirect_to_website",
            {
                "HttpResponse": make_response,
                "requests": NoNetwork(),
                "redirect": reject_redirect,
            },
        )
        for params in (
            {},
            {"appUrl": "https://posthog.com"},
            {"appUrl": "https://attacker.example"},
            {"appUrl": "http://localhost"},
        ):
            with self.subTest(params=params):
                request = SimpleNamespace(GET=params, user=TrapUser())
                result = func(request)
                self.assertEqual(result.status_code, 404)
                self.assertEqual(result.body, "")

    def test_forum_toolbar_entry_fails_before_accessing_user_or_rendering(self):
        def forbidden_render(*args, **kwargs):
            raise AssertionError("Inherited forum consent template rendered")

        func = real_function(
            TOOLBAR_SOURCE,
            "authorize_and_redirect",
            {
                "HttpResponse": make_response,
                "HttpRequest": object,
                "render_template": forbidden_render,
                "cast": lambda _, value: value,
                "User": object,
                "urlparse": urlparse,
                "urlencode": urlencode,
            },
        )
        for flag in ("true", "TRUE", "TrUe"):
            request = SimpleNamespace(
                GET={"forum_login": flag, "redirect": "https://posthog.com"},
                headers={"referer": "https://posthog.com"},
                user=TrapUser(),
            )
            self.assertEqual(func(request).status_code, 404)

    def test_regular_toolbar_authorization_still_renders_original_flow(self):
        rendered = []

        def capture_template(template, request, context=None, **kwargs):
            rendered.append((template, context))
            return make_response("safe toolbar")

        func = real_function(
            TOOLBAR_SOURCE,
            "authorize_and_redirect",
            {
                "HttpResponse": make_response,
                "HttpRequest": object,
                "render_template": capture_template,
                "cast": lambda _, value: value,
                "User": object,
                "urlparse": urlparse,
                "urlencode": urlencode,
                "hostname_in_allowed_url_list": lambda hosts, host: host == "local.flind.test",
                "settings": SimpleNamespace(SITE_URL="http://localhost:8010"),
            },
        )
        request = SimpleNamespace(
            GET={"redirect": "https://local.flind.test/dashboard"},
            headers={"referer": "https://local.flind.test/page"},
            user=SimpleNamespace(team=SimpleNamespace(app_urls=["https://local.flind.test"]), email="local@test.invalid"),
        )
        result = func(request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(rendered[0][0], "authorize_and_redirect.html")
        self.assertIn("/api/user/redirect_to_site/", rendered[0][1]["authorization_url"])

    def test_legacy_route_remains_usable_as_a_safe_not_found(self):
        urls = (ROOT / "posthog/urls.py").read_text()
        self.assertIn('opt_slash_path("api/user/redirect_to_website", user.redirect_to_website)', urls)
        template = FORUM_TEMPLATE.read_text()
        self.assertNotIn("/api/user/redirect_to_website/", template)
        self.assertNotIn("{{ email }}", template)
        self.assertNotIn("https://posthog.com/auth", template)

    def test_inherited_provider_credentials_are_absent_from_sso_function(self):
        source = USER_SOURCE.read_text()
        tree = ast.parse(source)
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "redirect_to_website")
        block = ast.get_source_segment(source, function)
        for forbidden in (
            "requests.request", "secrets.token_hex", "jwt.encode",
            "squeak.posthog.cc", "posthog.com/auth", "strapi_id",
            "JWT_SECRET_STRAPI",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, block)


if __name__ == "__main__":
    unittest.main()
