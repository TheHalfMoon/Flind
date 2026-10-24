"""Guard the Flind CLI Node-child analytics boundary without requiring Cargo."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cli/src/api_proxy.rs"


class CliProxyAnalyticsIsolationTests(unittest.TestCase):
    def test_no_vendor_analytics_ingest_host_or_build_token_injection(self) -> None:
        source = SOURCE.read_text()
        self.assertNotIn("https://us.i.post" + "hog.com", source)
        self.assertNotIn("option_env!(\"POSTHOG_API_TOKEN\")", source)
        self.assertNotIn("fn inject_analytics_env(", source)

    def test_child_inherited_analytics_environment_is_scrubbed(self) -> None:
        source = SOURCE.read_text()
        self.assertIn("isolate_inherited_analytics(&mut cmd);", source)
        for key in ("POSTHOG_ANALYTICS_API_KEY", "POSTHOG_ANALYTICS_HOST",
                    "POSTHOG_CLI_INVOCATION_ID"):
            with self.subTest(variable=key):
                self.assertIn('cmd.env_remove("' + key + '");', source)
        self.assertNotIn('cmd.env("POSTHOG_CLI_INVOCATION_ID",', source)

    def test_user_api_credential_injection_is_still_present(self) -> None:
        source = SOURCE.read_text()
        self.assertIn("inject_credentials(&mut cmd, invocation_context);", source)
        self.assertIn('cmd.env("POSTHOG_CLI_API_KEY", &config.api_key);', source)
        self.assertIn('cmd.env("POSTHOG_CLI_PROJECT_ID", &config.env_id);', source)
        self.assertIn('cmd.env("POSTHOG_CLI_HOST", &config.host);', source)

    def test_rust_runtime_command_env_assertion_exists(self) -> None:
        source = SOURCE.read_text()
        self.assertIn("fn analytics_settings_are_explicitly_removed_from_node_child()", source)
        self.assertIn("child.get_envs().collect()", source)
        self.assertIn("value.is_none()", source)
        self.assertIn('s == "user-api-key"', source)

    def test_comment_does_not_claim_full_network_isolation(self) -> None:
        source = SOURCE.read_text()
        self.assertIn("independent runtime egress audit", source)


if __name__ == "__main__":
    unittest.main()
