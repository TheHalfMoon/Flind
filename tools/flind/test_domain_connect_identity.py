"""Flind provider-identity and example-template safety checks.

These tests are independent of Django; full Domain Connect integration still
requires providers to register Flind templates and an isolated live test domain.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from flind.domain_connect_identity import allowed_flind_callback, valid_provider_id

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "frontend/src/lib/components/DomainConnect/templates"
LEGACY = "post" + "hog"
TEMPLATES = (
    "flind.example.email-verification-us.json",
    "flind.example.email-verification-eu.json",
    "flind.example.reverse-proxy-us.json",
    "flind.example.reverse-proxy-eu.json",
)


class FlindDomainConnectIdentityTests(unittest.TestCase):
    def test_domain_provider_ids_validate_without_runtime_deps(self) -> None:
        for value in ("flind.example", "flind.si", "dns.flind.example"):
            with self.subTest(value=value):
                self.assertTrue(valid_provider_id(value))
        for value in (
            "", None, "localhost", "https://flind.example", "FLIND.EXAMPLE",
            "flind.example:443", "user@flind.example", "flind..example",
            "-flind.example", "flind-.example", "flind.example/path", "127.0.0.1",
        ):
            with self.subTest(value=value):
                self.assertFalse(valid_provider_id(value))

    def test_no_inherited_dns_template_paths(self) -> None:
        names = [p.name for p in DIRECTORY.glob("*.json")]
        self.assertEqual(set(names), set(TEMPLATES))
        for name in names:
            self.assertNotIn(LEGACY, name.casefold())

    def test_flind_drafts_do_not_claim_external_provider_registration(self) -> None:
        for name in TEMPLATES:
            with self.subTest(name=name):
                data = json.loads((DIRECTORY / name).read_text())
                self.assertEqual(data["providerId"], "flind.example")
                self.assertEqual(data["providerName"], "Flind")
                self.assertEqual(data["syncPubKeyDomain"], "domainconnect.flind.example")
                self.assertEqual(data["logoUrl"], "https://flind.example/flind-logo.svg")
                self.assertTrue(data["syncRedirectDomain"].endswith(".flind.example"))
                self.assertNotIn(LEGACY, json.dumps(data).lower())
                self.assertEqual(data["version"], 1)

    def test_template_variables_still_match_payload_contract(self) -> None:
        for name in TEMPLATES:
            with self.subTest(name=name):
                data = json.loads((DIRECTORY / name).read_text())
                variables = set()
                for record in data["records"]:
                    for value in record.values():
                        if isinstance(value, str):
                            variables.update(re.findall(r"%([A-Za-z][A-Za-z0-9]*)%", value))
                if "email-verification" in name:
                    self.assertEqual(variables, {"verifyToken", "dkim1", "dkim2", "dkim3", "mailFromSub", "sesRegion"})
                else:
                    self.assertEqual(variables, {"target"})
                    self.assertTrue(data["hostRequired"])

    def test_backend_requires_flind_registration_before_dns_or_ses(self) -> None:
        source = (ROOT / "posthog/domain_connect.py").read_text()
        endpoint = (ROOT / "posthog/api/integration.py").read_text()
        settings = (ROOT / "posthog/settings/web.py").read_text()
        self.assertIn('FLIND_DOMAIN_CONNECT_ENABLED", False', settings)
        self.assertIn('FLIND_DOMAIN_CONNECT_PROVIDER_ID", ""', settings)
        self.assertIn("def flind_domain_connect_provider_id()", source)
        self.assertIn("if flind_domain_connect_provider_id() is None:", source)
        self.assertIn("provider_id=provider_id,", source)
        self.assertIn("if flind_domain_connect_provider_id() is None:", endpoint)
        self.assertNotIn('provider_id="' + LEGACY + '.com"', source)

    def test_callbacks_cannot_escape_flind_origin(self) -> None:
        allowed = (
            "https://flind.example/settings?domain_connect=email",
            "https://flind.example/account",
        )
        for uri in allowed:
            with self.subTest(uri=uri):
                self.assertTrue(allowed_flind_callback(uri, "https://flind.example"))
        hostile = (
            "https://untrusted.example/settings",
            "https://flind.example.untrusted.example/",
            "https://flind.example:444/settings",
            "http://flind.example/settings",
            "https://user@flind.example/settings",
            "https://flind.example/settings#not-allowed",
            "//flind.example/settings",
            "javascript:alert(1)",
            "https://flind.example/\\evil",
            "",
        )
        for uri in hostile:
            with self.subTest(uri=uri):
                self.assertFalse(allowed_flind_callback(uri, "https://flind.example"))
        self.assertTrue(allowed_flind_callback("http://localhost:8010/settings", "http://localhost:8010"))
        self.assertFalse(allowed_flind_callback("http://flind.example/settings", "http://flind.example"))

    def test_dns_check_returns_early_in_unregistered_flind(self) -> None:
        source = (ROOT / "posthog/api/integration.py").read_text()
        self.assertIn('return Response({"supported": False, "provider_name": None, "available_providers": []})', source)
        self.assertIn("Domain Connect callback must stay on this Flind instance", source)

    def test_unregistered_drafts_are_not_reported_as_live(self) -> None:
        readme = (DIRECTORY.parent / "README.md").read_text()
        self.assertIn("draft examples", readme)
        self.assertIn("disabled by default", readme)
        self.assertNotIn(LEGACY + ".com", readme)


if __name__ == "__main__":
    unittest.main()
