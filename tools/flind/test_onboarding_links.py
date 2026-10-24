"""Protect first-party onboarding legal and support destinations in Flind."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRE = ROOT / "frontend/src/scenes/PreflightCheck/PreflightCheck.tsx"
ORG = ROOT / "frontend/src/scenes/organization/ConfirmOrganization/ConfirmOrganization.tsx"
LINKS = ROOT / "frontend/src/lib/flindPublicLinks.ts"


class FirstPartyOnboardingLinkTests(unittest.TestCase):
    def test_preflight_help_is_never_implicitly_external(self) -> None:
        code = PRE.read_text()
        self.assertNotIn("https://post" + "hog.com/", code)
        self.assertIn("flindPublicUrl('docs')", code)
        self.assertIn("flindPublicUrl('community')", code)
        self.assertIn("Contact your Flind workspace administrator", code)

    def test_org_creation_does_not_claim_other_company_legal_terms(self) -> None:
        code = ORG.read_text()
        self.assertNotIn("https://post" + "hog.com/", code)
        self.assertNotIn("Your Post" + "Hog account", code)
        self.assertNotIn("Hogflix Movies", code)
        self.assertIn("termsUrl && privacyUrl", code)
        self.assertIn("Legal policies for this Flind instance have not been configured", code)
        self.assertIn("flindPublicUrl('terms')", code)
        self.assertIn("flindPublicUrl('privacy')", code)

    def test_legal_destinations_use_existing_flind_origin_gate(self) -> None:
        code = LINKS.read_text()
        for key in ("terms", "privacy"):
            self.assertIn("'" + key + "'", code)
            self.assertIn("VITE_FLIND_" + key.upper() + "_URL", code)
        self.assertIn("url.hostname !== hostname", code)
        self.assertIn("url.protocol !== 'https:'", code)

    def test_unconfigured_docs_and_community_have_visible_local_guidance(self) -> None:
        for path in (PRE, ORG):
            with self.subTest(path=str(path)):
                content = path.read_text()
                self.assertIn("Flind workspace administrator", content)
                self.assertIn("docsUrl", content)
                self.assertIn("communityUrl", content)


if __name__ == "__main__":
    unittest.main()
