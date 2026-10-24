"""Flind CLI updates must never execute an inherited release script."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPDATER = ROOT / "cli/src/update.rs"


class FlindCliUpdaterIsolationTests(unittest.TestCase):
    def test_no_inherited_download_or_install_endpoints(self) -> None:
        source = UPDATER.read_text()
        self.assertNotIn("releases.post" + "hog.com", source)
        for old in ("MANIFEST_URL", "INSTALL_SH_URL", "INSTALL_PS1_URL"):
            self.assertNotIn(old, source)

    def test_update_fails_closed_without_a_release_channel(self) -> None:
        source = UPDATER.read_text()
        begin = source.index("pub fn update() -> Result<()> {")
        end = source.index("\n#[cfg(test)]", begin)
        body = source[begin:end]
        self.assertIn("anyhow::bail!", body)
        self.assertIn("Flind CLI self-update is disabled", body)
        self.assertNotIn("reqwest", body)
        self.assertNotIn("Command::new", body)

    def test_no_runtime_download_then_shell_execution(self) -> None:
        source = UPDATER.read_text()
        self.assertNotIn("reqwest::blocking", source)
        self.assertNotIn('Command::new("sh")', source)
        self.assertNotIn("curl -LsSf", source)
        self.assertNotIn("irm https://", source)

    def test_explicit_rust_runtime_regression_exists(self) -> None:
        source = UPDATER.read_text()
        self.assertIn("fn self_update_fails_closed_without_a_release_channel()", source)
        self.assertIn("let message = update().unwrap_err().to_string();", source)

    def test_does_not_suggest_inherited_package_manager_release(self) -> None:
        source = UPDATER.read_text()
        self.assertNotIn("brew upgrade post" + "hog-cli", source)
        self.assertNotIn("cargo install post" + "hog-cli", source)
        self.assertIn("No verified Flind CLI package is published", source)


if __name__ == "__main__":
    unittest.main()
