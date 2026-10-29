"""Guard CLI credential, login and network-origin boundary by inspecting Rust source."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "cli/src/utils/auth.rs"
LOGIN = ROOT / "cli/src/login.rs"
CTX = ROOT / "cli/src/invocation_context.rs"


class CliHostValidationWave23Tests(unittest.TestCase):
    def test_configured_hosts_are_validated_before_client_creation(self):
        auth = AUTH.read_text(encoding="utf-8")
        ctx = CTX.read_text(encoding="utf-8")
        self.assertIn('Url::parse(host)', auth)
        self.assertIn('hostname == "posthog.com" || hostname.ends_with(".posthog.com")', auth)
        self.assertIn('url.scheme() == "https"', auth)
        self.assertIn("trim_end_matches('.')", auth)
        self.assertIn('url.username().is_empty()', auth)
        self.assertIn('url.query().is_some()', auth)
        self.assertIn('url.fragment().is_some()', auth)
        self.assertIn('host_validator(&self.host)', ctx)

    def test_oauth_device_login_rejects_unqualified_host_before_network(self):
        login = LOGIN.read_text(encoding="utf-8")
        start = login.index('pub fn login_with_use_cases(')
        guard = login.index('host_validator(&host)', start)
        request = login.index('request_device_code(&host)?', start)
        self.assertLess(guard, request)
        self.assertIn('Flind login requires an approved HTTPS instance', login)

    def test_no_automatic_http_redirects_in_device_flow(self):
        login = LOGIN.read_text(encoding="utf-8")
        self.assertEqual(login.count('.redirect(reqwest::redirect::Policy::none())'), 2)
        self.assertEqual(login.count('reqwest::blocking::Client::new()'), 0)

    def test_rust_tests_cover_allowed_and_disallowed_hosts(self):
        auth = AUTH.read_text(encoding="utf-8")
        login = LOGIN.read_text(encoding="utf-8")
        self.assertIn('fn validator_refuses_upstream_hosts_and_secret_bearing_urls()', auth)
        self.assertIn('fn validator_accepts_explicit_tls_and_local_development_hosts()', auth)
        self.assertIn('fn inherited_oauth_host_is_not_eligible_for_login()', login)


if __name__ == "__main__":
    unittest.main()
