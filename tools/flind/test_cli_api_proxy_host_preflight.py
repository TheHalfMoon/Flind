"""Reject API CLI proxy paths that bypass host validation before Node launch.

Dependency-free guard. Native Cargo tests validate runtime behavior separately.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "cli/src/api_proxy.rs").read_text(encoding="utf-8")
AUTH = (ROOT / "cli/src/utils/auth.rs").read_text(encoding="utf-8")
TEST = (ROOT / "cli/tests/api_proxy.rs").read_text(encoding="utf-8")


class CliApiHostPreflightTests(unittest.TestCase):
    def test_all_configuration_channels_are_validated_before_node(self):
        self.assertIn("fn approved_proxy_host(", SOURCE)
        self.assertIn("host_validator(value)", SOURCE)
        for v in ("explicit_host", "legacy_host", "cli_host", "credential_host"):
            self.assertIn(v, SOURCE)
        self.assertIn('env::var("POSTHOG_HOST").ok().as_deref()', SOURCE)
        self.assertIn('env::var("POSTHOG_CLI_HOST").ok().as_deref()', SOURCE)
        self.assertIn('invocation_context.map(|ctx| ctx.config.host.as_str())', SOURCE)
        runner = SOURCE.split("pub fn run(", 1)[1].split("#[cfg(test)]", 1)[0]
        guard = runner.index("approved_proxy_host(")
        script = runner.index("find_script()")
        child = runner.index('Command::new("node")')
        self.assertLess(guard, script)
        self.assertLess(script, child)

    def test_conflicting_aliases_rejected_and_child_receives_one_origin(self):
        self.assertIn("Url::parse(value)?.origin() != chosen_origin", SOURCE)
        self.assertIn("rejected conflicting", SOURCE)
        self.assertIn("requires an explicit, approved instance host", SOURCE)
        self.assertIn('cmd.env_remove("POSTHOG_HOST");', SOURCE)
        self.assertIn('cmd.env("POSTHOG_CLI_HOST", approved_host);', SOURCE)
        self.assertIn("Ok(chosen_origin.ascii_serialization())", SOURCE)
        self.assertIn('hostname == "posthog.com"', AUTH)
        self.assertIn('hostname.ends_with(".posthog.com")', AUTH)

    def test_native_negative_tests_cover_real_node_nonexecution(self):
        for fragment in (
            "api_rejects_unowned_host_before_the_node_child_runs",
            "api_without_explicit_host_refuses_unqualified_embedded_defaults",
            "api_conflicting_host_aliases_fail_before_launch",
            "assert!(!stderr.contains(",
            "Node must not run with an inherited cloud API host",
            "api_forwards_all_arguments_to_the_script",
        ):
            self.assertIn(fragment, TEST)


if __name__ == "__main__":
    unittest.main()
