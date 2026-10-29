"""CLI login should never default to another provider's authentication endpoints."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGIN = ROOT / "cli/src/login.rs"
AUTH = ROOT / "cli/src/utils/auth.rs"


class FlindCliLoginHostTests(unittest.TestCase):
    def test_login_has_no_inherited_region_or_manual_defaults(self) -> None:
        source = LOGIN.read_text(encoding="utf-8")
        self.assertNotIn("https://us.post" + "hog.com", source)
        self.assertNotIn("https://eu.post" + "hog.com", source)
        self.assertNotIn("Select your Post" + "Hog region", source)
        self.assertNotIn("with_default(", source)
        self.assertIn("return manual_login();", source)

    def test_operator_host_is_required_for_device_flow(self) -> None:
        source = LOGIN.read_text(encoding="utf-8")
        self.assertIn("let Some(host) = approved_login_host(host_override) else", source)
        self.assertIn("host_override", source)
        self.assertIn("approved_login_host(None), None", source)
        self.assertIn("approved_login_host(Some(\"http://localhost:8000\".into()))", source)

    def test_manual_login_needs_explicit_host_and_has_first_party_copy(self) -> None:
        source = LOGIN.read_text(encoding="utf-8")
        self.assertIn('Text::new("Enter your Flind instance URL")', source)
        self.assertIn("with_validator(host_validator)", source)
        self.assertIn("Flind workspace administrator", source)
        self.assertNotIn("post" + "hog.com/docs/api", source)

    def test_auth_token_host_does_not_default_to_vendor_cloud(self) -> None:
        source = AUTH.read_text(encoding="utf-8")
        self.assertNotIn('unwrap_or("https://us.post' + 'hog.com"', source)
        self.assertIn("self.host.clone().unwrap_or_default()", source)
        self.assertIn('assert_eq!(token.get_host(), "")', source)
        self.assertIn('http://localhost:8000', source)


if __name__ == "__main__":
    unittest.main()
