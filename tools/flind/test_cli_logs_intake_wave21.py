"""Static defense-in-depth checks for explicit CLI logs intake boundaries.

These checks intentionally do not substitute for the Rust unit tests or live
HTTP tests. The Rust tests exercise URL parsing and rejection conditions.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "cli/src/experimental/logs/run.rs"
COMMAND = ROOT / "cli/src/experimental/logs/command.rs"


class CliLogsIntakeWave21Tests(unittest.TestCase):
    def test_intake_url_is_fallible_not_blind_string_concatenation(self):
        run = RUN.read_text()
        self.assertIn("pub fn intake_url(host: &str, from: chrono::DateTime<chrono::Utc>) -> Result<String>", run)
        self.assertIn('reqwest::Url::parse(host)', run)
        self.assertIn('base.query_pairs_mut()', run)
        self.assertIn('base.set_path("/i/v1/logs")', run)
        self.assertNotIn("host.trim_end_matches('/')", run)

    def test_inherited_cloud_and_untrusted_origins_denied(self):
        run = RUN.read_text()
        self.assertIn('hostname == "posthog.com" || hostname.ends_with(".posthog.com")', run)
        self.assertIn('hostname.ends_with(".localhost")', run)
        self.assertIn('parse::<IpAddr>()', run)
        self.assertIn('base.scheme() == "https"', run)
        self.assertIn('base.username().is_empty()', run)
        self.assertIn('base.query().is_some()', run)
        self.assertIn('base.fragment().is_some()', run)
        self.assertIn('base.path() != "/"', run)

    def test_no_credential_redirects_for_import_or_dry_run(self):
        cmd = COMMAND.read_text()
        self.assertEqual(cmd.count('.redirect(reqwest::redirect::Policy::none())'), 2)
        self.assertIn('intake_url(&host, config.range.from)?', cmd)
        self.assertNotIn('intake_url: intake_url(&host, config.range.from),', cmd)
        self.assertNotIn('Import historical logs from another log store into PostHog', cmd)

    def test_target_validation_scenarios_in_rust_tests(self):
        run = RUN.read_text()
        self.assertIn('fn intake_refuses_upstream_hosts_and_url_ambiguity()', run)
        self.assertIn('fn intake_supports_explicit_tls_and_loopback_development()', run)
        self.assertIn('"https://us.i.posthog.com"', run)
        self.assertIn('"https://user:password@flind.example"', run)


if __name__ == "__main__":
    unittest.main()
