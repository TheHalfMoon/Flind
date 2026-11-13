"""Fail-closed source acceptance for Rust Flind CLI diagnostic egress.

This is a static regression; full Cargo unit tests and runtime network
inspection remain separate mandatory qualification steps.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
INVOCATION = (ROOT / "cli/src/invocation_context.rs").read_text(encoding="utf-8")
ERROR = (ROOT / "cli/src/error.rs").read_text(encoding="utf-8")
COMMANDS = (ROOT / "cli/src/commands.rs").read_text(encoding="utf-8")


class CliTelemetryNoDonorTests(unittest.TestCase):
    def test_telemetry_guard_is_unconditionally_false(self) -> None:
        self.assertRegex(
            INVOCATION,
            r"pub fn external_telemetry_allowed\(\) -> bool \{\s*false\s*\}",
        )
        self.assertNotIn("FLIND_CLI_TELEMETRY_OPT_IN", INVOCATION)

    def test_direct_cli_telemetry_is_guarded_before_emit(self) -> None:
        sections = (
            (
                INVOCATION,
                "pub fn capture_command_run_without_context()",
                "posthog_rs::capture(",
                "if !external_telemetry_allowed()",
            ),
            (
                INVOCATION,
                "pub fn capture_event(",
                "posthog_rs::capture(",
                "if !external_telemetry_allowed()",
            ),
            (
                ERROR,
                "fn capture_exception(",
                "posthog_rs::capture_exception_with(",
                "if !crate::invocation_context::external_telemetry_allowed()",
            ),
        )
        for source, entry, send, guard in sections:
            with self.subTest(entry=entry):
                start = source.index(entry)
                guard_index = source.index(guard, start)
                send_index = source.index(send, start)
                self.assertLess(guard_index, send_index)
                self.assertLess(send_index - guard_index, 10_000)

        # No additional unguarded emission elsewhere in native Rust CLI.
        cli_files = list((ROOT / "cli/src").rglob("*.rs"))
        matches = [(str(p.relative_to(ROOT)), m.group())
                   for p in cli_files
                   for m in re.finditer(
                       r"posthog_rs::(?:capture(?:_exception_with)?)\s*\(", p.read_text(encoding="utf-8")
                   )]
        self.assertEqual(len(matches), 3, matches)

    def test_api_and_error_routes_still_use_existing_guarded_hooks(self) -> None:
        self.assertIn("capture_command_run_without_context()", COMMANDS)
        self.assertIn("error.capture()", COMMANDS)
        self.assertIn("telemetry_stays_disabled_without_a_qualified_flind_endpoint", INVOCATION)
        self.assertIn("cli_failures_do_not_send_unqualified_exception_telemetry", ERROR)


if __name__ == "__main__":
    unittest.main()
