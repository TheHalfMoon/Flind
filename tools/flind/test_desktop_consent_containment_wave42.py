"""Protect Desktop consent from inherited vendor agreements and remote links."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONSENT = ROOT / "products/desktop/packages/ui/src/features/consent"


class DesktopConsentWave42Tests(unittest.TestCase):
    def test_no_mutations_of_inherited_consent_via_flind_desktop_ui(self):
        panel = (CONSENT / "ConsentPanel.tsx").read_text()
        for name in (
            "approveAiDataProcessing", "acceptDesktopBetaTerms",
            "AI_CONSENT_GRANTED_INAPP", "DESKTOP_BETA_TERMS_ACCEPTED_INAPP",
            "copySettingsLink", "navigator.clipboard.writeText",
        ):
            with self.subTest(token=name):
                self.assertNotIn(name, panel)
        self.assertIn("await consent.retry()", panel)

    def test_no_unverified_vendor_legal_copy_or_external_link(self):
        panel = (CONSENT / "ConsentPanel.tsx").read_text()
        for name in (
            "posthog.com", "PostHog", "Baseten", "Modal", "HIPAA",
            "PHI", "https://app.", "settingsUrl", "onAccept",
        ):
            with self.subTest(token=name):
                self.assertNotIn(name, panel)
        self.assertIn("Flind consent review required", panel)
        self.assertIn("Flind beta terms unavailable", panel)
        self.assertIn("AI data-processing approval unavailable", panel)

    def test_onboarding_still_requires_resolved_satisfied_server_state(self):
        step = (CONSENT / "ConsentStep.tsx").read_text()
        self.assertIn('consent.status !== "resolved"', step)
        self.assertIn("!consent.satisfied", step)
        self.assertIn("<ConsentPanel", step)
        self.assertNotIn("setIsSubmitting(", step)

    def test_native_vitest_checks_no_submission(self):
        tests = (CONSENT / "ConsentPanel.test.tsx").read_text()
        for text in (
            "not.toHaveBeenCalled()",
            'name: "Refresh"',
            'screen.queryByRole("link")',
            "Flind beta terms unavailable",
        ):
            self.assertIn(text, tests)


if __name__=="__main__":
    unittest.main()
