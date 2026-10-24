"""First-party CLI source constraints for telemetry and default API hosts."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / "cli/src/invocation_context.rs"
MAIN = ROOT / "cli/src/main.rs"


class CliRuntimeIsolationTests(unittest.TestCase):
    def test_cli_never_initializes_inherited_global_analytics_sdk(self) -> None:
        context = CONTEXT.read_text()
        main = MAIN.read_text()
        self.assertNotIn("posthog_rs::init_global", context)
        self.assertNotIn('option_env!("POSTHOG_API_TOKEN")', context)
        self.assertNotIn("init_posthog_telemetry", main)
        self.assertNotIn("posthog_rs::flush();", main)

    def test_no_implicit_provider_analytics_host_for_user_api(self) -> None:
        context = CONTEXT.read_text()
        self.assertNotIn("https://us.i.post" + "hog.com", context)
        self.assertIn("host: configured_api_host(host, token.host)?", context)
        self.assertIn("override_host.or(saved_host).context(", context)
        self.assertIn("Flind CLI API host is not configured", context)

    def test_preserves_explicit_local_or_flind_api_host(self) -> None:
        context = CONTEXT.read_text()
        self.assertIn("Some(\"https://my.flind.example\".into())", context)
        self.assertIn("Some(\"http://localhost:8000\".into())", context)
        self.assertIn("configured_api_host(None, None).is_err()", context)

    def test_source_side_network_capture_requires_further_testing(self) -> None:
        context = CONTEXT.read_text()
        self.assertIn("posthog_rs::capture(", context)
        self.assertIn("PHClient::from_config", context)
        self.assertNotIn("posthog_rs::init_global", context)


if __name__ == "__main__":
    unittest.main()
