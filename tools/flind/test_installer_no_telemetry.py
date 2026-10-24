"""Installer privacy regression: no inherited analytics client or domain capture."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "bin/hobby-installer"


class InstallerTelemetryIsolationTests(unittest.TestCase):
    def test_no_vendor_analytics_client_or_key(self) -> None:
        mod = (INSTALLER / "go.mod").read_text()
        self.assertNotIn("github.com/post" + "hog/posthog-go", mod)
        self.assertFalse((INSTALLER / "core/telemetry.go").exists())

    def test_no_install_start_or_complete_events(self) -> None:
        installer = (INSTALLER / "core/install.go").read_text()
        for value in (
            "SendInstallStartEvent", "SendInstallCompleteEvent",
            'Name: "Send telemetry"', 'Name: "Send completion telemetry"',
        ):
            self.assertNotIn(value, installer)
        self.assertIn('Name: "Setup git"', installer)

    def test_no_deferred_analytics_shutdown(self) -> None:
        main = (INSTALLER / "main.go").read_text()
        self.assertNotIn("CloseTelemetry()", main)
        self.assertIn("core.CloseLogFile()", main)

    def test_go_runtime_test_covers_installer_step_list(self) -> None:
        test = (INSTALLER / "core/no_telemetry_test.go").read_text()
        self.assertIn("GetInstallSteps()", test)
        self.assertIn("TestInstallerContainsNoTelemetrySteps", test)


if __name__ == "__main__":
    unittest.main()
