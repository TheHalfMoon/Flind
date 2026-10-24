"""Django HTTP regression tests for Flind-owned security.txt."""
from datetime import datetime, timedelta, timezone

from django.test import RequestFactory, SimpleTestCase, override_settings

from posthog.views import security_txt


class TestFlindSecurityTxt(SimpleTestCase):
    @override_settings(FLIND_SECURITY_CONTACT="", FLIND_SECURITY_EXPIRES="")
    def test_unconfigured_security_contact_returns_404(self):
        response = security_txt(RequestFactory().get("/.well-known/security.txt"))
        self.assertEqual(response.status_code, 404)

    def test_valid_flind_contact_returns_current_security_txt(self):
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        with override_settings(
            FLIND_SECURITY_CONTACT="mailto:security@flind.example",
            FLIND_SECURITY_EXPIRES=expires,
        ):
            response = security_txt(RequestFactory().get("/.well-known/security.txt"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Contact: mailto:security@flind.example", response.content)
        self.assertIn(b"Expires: ", response.content)

    def test_invalid_operator_input_does_not_publish_security_contact(self):
        with override_settings(
            FLIND_SECURITY_CONTACT="mailto:security@flind.example\nContact: mailto:evil@example.com",
            FLIND_SECURITY_EXPIRES=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        ):
            response = security_txt(RequestFactory().get("/.well-known/security.txt"))
        self.assertEqual(response.status_code, 404)
