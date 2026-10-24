"""Ensure Flind Mobile never accepts inherited terms or redirects from consent."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MOBILE = ROOT / "products/desktop/apps/mobile/src"


class MobileLegalConsentWave39Tests(unittest.TestCase):
    def test_approval_mutation_calls_are_not_exposed(self):
        screen = (MOBILE / "app/consent.tsx").read_text()
        for forbidden in (
            "approveAiDataProcessing(",
            "acceptDesktopBetaTerms(",
            "onAcceptAi=",
            "onAcceptBeta=",
            "ANALYTICS_EVENTS.AI_CONSENT_GRANTED",
            "ANALYTICS_EVENTS.DESKTOP_BETA_TERMS_ACCEPTED",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, screen)
        self.assertIn("await logout()", screen)

    def test_neither_inherited_vendor_claims_nor_external_legal_links_are_in_ui(self):
        panel = (MOBILE / "features/consent/components/ConsentPanel.tsx").read_text()
        screen = (MOBILE / "app/consent.tsx").read_text()
        for forbidden in (
            "posthog.com", "PostHog", "Baseten", "Modal", "onAccept",
            "openExternalUrl", "Approved", "onPress",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, panel)
        self.assertNotIn("EXTERNAL_LINKS.discord", screen)
        self.assertNotIn("openExternalUrl", screen)
        self.assertIn("Flind consent review required", panel)
        self.assertIn("Flind beta terms unavailable", panel)

    def test_organization_consent_remains_gated(self):
        source = (MOBILE / "app/consent.tsx").read_text()
        self.assertIn("!consent.satisfied", source)
        self.assertIn("needsAiConsent={consent.needsAiConsent}", source)
        self.assertIn("needsBetaTerms={consent.needsBetaTerms}", source)
        self.assertIn("Support link not configured", source)


if __name__ == "__main__":
    unittest.main()
