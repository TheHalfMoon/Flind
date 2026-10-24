"""No externally hosted browser telemetry may be bootstrapped by Flind."""

from __future__ import annotations

import unittest
from pathlib import Path

from flind.browser_capture import browser_capture_context

ROOT = Path(__file__).resolve().parents[2]
VENDOR = "post" + "hog"


class FlindBrowserCaptureTests(unittest.TestCase):
    def test_default_production_browser_bootstrap_is_empty(self) -> None:
        self.assertEqual(browser_capture_context(), {})
        self.assertEqual(browser_capture_context(e2e_token="test-only"), {})
        self.assertEqual(browser_capture_context(self_token="local-project"), {})

    def test_unconfigured_e2e_capture_never_inherits_token(self) -> None:
        self.assertEqual(browser_capture_context(e2e_testing=True), {})
        self.assertEqual(
            browser_capture_context(
                e2e_testing=True,
                self_capture=True,
                self_token="other-team-token",
            ),
            {},
        )

    def test_e2e_fixture_uses_only_same_origin(self) -> None:
        self.assertEqual(
            browser_capture_context(e2e_testing=True, e2e_token="test-token"),
            {"js_posthog_api_key": "test-token", "js_posthog_host": ""},
        )

    def test_local_self_capture_uses_only_first_party(self) -> None:
        self.assertEqual(browser_capture_context(self_capture=True), {})
        self.assertEqual(
            browser_capture_context(self_capture=True, self_token="local-team-token"),
            {"js_posthog_api_key": "local-team-token", "js_posthog_host": ""},
        )

    def test_e2e_fixture_takes_precedence_over_self_capture(self) -> None:
        self.assertEqual(
            browser_capture_context(
                e2e_testing=True,
                self_capture=True,
                e2e_token="fixture-token",
                self_token="ordinary-user-token",
            ),
            {"js_posthog_api_key": "fixture-token", "js_posthog_host": ""},
        )

    def test_invalid_tokens_never_enable_capture(self) -> None:
        for token in ("", " ", None, 42, [], {}):
            with self.subTest(token=token):
                self.assertEqual(
                    browser_capture_context(e2e_testing=True, e2e_token=token), {}
                )

    def test_legacy_analytics_cloud_secret_is_not_shipped(self) -> None:
        constants = (ROOT / "posthog/constants.py").read_text()
        source = (ROOT / "posthog/utils.py").read_text()
        self.assertNotIn("POSTHOG_JS_CLOUD_HOST", constants)
        self.assertNotIn("POSTHOG_JS_CLOUD_TOKEN", constants)
        self.assertNotIn("POSTHOG_JS_CLOUD_HOST", source)
        self.assertNotIn("POSTHOG_JS_CLOUD_TOKEN", source)
        self.assertNotIn("internal-cf." + VENDOR + ".com", source)
        self.assertNotIn("us." + VENDOR + ".com", source)

    def test_backend_scrubs_caller_supplied_tokens_before_resolving_local_team(self) -> None:
        source = (ROOT / "posthog/utils.py").read_text()
        self.assertIn('for key in ("js_posthog_api_key", "js_posthog_host", "js_posthog_ui_host"):', source)
        self.assertIn("context.pop(key, None)", source)
        self.assertIn("browser_capture_context(e2e_testing=True", source.replace("\n                ", ""))
        self.assertIn("browser_capture_context(self_capture=True, self_token=self_token)", source)

    def test_settings_default_to_no_fixture_capture(self) -> None:
        settings = (ROOT / "posthog/settings/base_variables.py").read_text()
        self.assertIn('get_from_env("FLIND_E2E_CAPTURE_TOKEN", "")', settings)

    def test_html_instrumentation_is_conditional_on_local_token(self) -> None:
        source = (ROOT / "posthog/templates/head.html").read_text()
        self.assertIn("{% if not opt_out_capture and js_posthog_api_key %}", source)


if __name__ == "__main__":
    unittest.main()
