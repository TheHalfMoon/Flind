"""Flind security contact protocol, validation and backend integration gates."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flind.security_contact import security_txt_content

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)
FUTURE = (NOW + timedelta(days=30)).isoformat()


class FlindSecurityContactTests(unittest.TestCase):
    def test_not_advertised_without_operator_input(self) -> None:
        self.assertIsNone(security_txt_content("", "", now=NOW))
        self.assertIsNone(security_txt_content("mailto:security@flind.example", "", now=NOW))

    def test_valid_email_contact_has_unexpired_utc_date(self) -> None:
        record = security_txt_content("mailto:security@flind.example", FUTURE, now=NOW)
        self.assertEqual(record, "Contact: mailto:security@flind.example\nExpires: 2026-11-23T00:00:00Z\n")

    def test_valid_https_contact(self) -> None:
        record = security_txt_content("https://flind.example/security", FUTURE, now=NOW)
        self.assertIn("Contact: https://flind.example/security", record or "")

    def test_rejects_untrusted_protocols_and_header_injection(self) -> None:
        for contact in (
            "http://flind.example/security",
            "mailto:user@flind.example\nContact: mailto:fake@other.example",
            "https://flind.example/security#fragment",
            "https://user@flind.example/contact",
            "javascript:alert(1)",
            "mailto:missing-domain",
            "mailto:broken@@flind.example",
            "https://flind.example:8443/security",
        ):
            with self.subTest(contact=contact):
                self.assertIsNone(security_txt_content(contact, FUTURE, now=NOW))

    def test_rejects_expired_and_overlong_validity_windows(self) -> None:
        for expiry in ("2024-03-14T00:00:00Z", "2026-11-23", "2099-01-01T00:00:00Z", ""):
            with self.subTest(expiry=expiry):
                self.assertIsNone(security_txt_content("mailto:security@flind.example", expiry, now=NOW))

    def test_exact_old_vendor_contact_removed(self) -> None:
        source = (ROOT / "posthog/views.py").read_text()
        self.assertNotIn("engineering@post" + "hog.com", source)
        self.assertNotIn("https://post" + "hog.com/careers", source)
        self.assertIn("return HttpResponse(status=404)", source)

    def test_operator_settings_default_empty(self) -> None:
        source = (ROOT / "posthog/settings/web.py").read_text()
        self.assertIn('FLIND_SECURITY_CONTACT: str = os.getenv("FLIND_SECURITY_CONTACT", "")', source)
        self.assertIn('FLIND_SECURITY_EXPIRES: str = os.getenv("FLIND_SECURITY_EXPIRES", "")', source)


if __name__ == "__main__":
    unittest.main()
