"""Flind Rust->Node API proxy rejects unqualified subcommand host overrides."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROXY = (ROOT / "cli/src/api_proxy.rs").read_text(encoding="utf-8")
BINARY = (ROOT / "cli/tests/api_proxy.rs").read_text(encoding="utf-8")


class CliNestedHostAndNodeHookTests(unittest.TestCase):
    def test_nested_transport_options_blocked_before_loading_node_script(self):
        run = PROXY.split("pub fn run(", 1)[1].split("#[cfg(test)]", 1)[0]
        self.assertIn("fn reject_nested_host_overrides(args: &[String])", PROXY)
        self.assertIn("flag.eq_ignore_ascii_case(name)", PROXY)
        self.assertIn("arg.split_once('=')", PROXY)
        for flag in ("--host", "--api-host", "--api-url", "--base-url", "--server-url", "--config", "--config-file"):
            self.assertIn('"' + flag + '"', PROXY)
        self.assertIn("reject_nested_host_overrides(&args).map_err(CapturedError::from)?;", run)
        self.assertLess(run.index("reject_nested_host_overrides(&args)"), run.index("find_script()"))
        self.assertLess(run.index("reject_nested_host_overrides(&args)"), run.index('Command::new("node")'))

    def test_node_preload_and_module_path_are_not_inherited_with_api_credentials(self):
        isolate = PROXY.split("fn isolate_inherited_analytics(cmd: &mut Command)", 1)[1].split("\n}", 1)[0]
        for name in ("NODE_OPTIONS", "NODE_PATH", "POSTHOG_ANALYTICS_API_KEY", "POSTHOG_ANALYTICS_HOST"):
            self.assertIn('cmd.env_remove("' + name + '")', isolate)
        self.assertIn('child.env("NODE_OPTIONS",', PROXY)
        self.assertIn('child.env("NODE_PATH",', PROXY)
        self.assertIn('cmd.env("POSTHOG_CLI_HOST", approved_host)', PROXY)

    def test_native_negative_process_will_not_start_node(self):
        self.assertIn("fn api_nested_host_override_is_denied_before_embedded_node_starts()", BINARY)
        self.assertIn("unqualified Node bundle must not execute on nested host override", BINARY)
        self.assertIn("rejected a nested server/config override", BINARY)
        self.assertIn("fn api_forwards_all_arguments_to_the_script()", BINARY)
        self.assertIn('.env("NODE_OPTIONS", format!', BINARY)
        self.assertIn('assert!(!preloaded.exists()', BINARY)

    def test_normal_metadata_and_tool_payload_are_still_accepted(self):
        self.assertIn("fn normal_agent_tool_arguments_and_payloads_still_pass()", PROXY)
        self.assertIn('vec!["tools", "--json"]', PROXY)
        self.assertIn('vec!["search", "host"]', PROXY)
        self.assertIn("fn nested_node_transport_and_config_flags_are_rejected_before_credentials()", PROXY)


if __name__ == "__main__":
    unittest.main()
