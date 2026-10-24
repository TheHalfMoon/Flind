"""Prevent unsupported vendor billing and fake payment CTAs in Flind Desktop."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "products/desktop"
UI = DESKTOP / "packages/ui/src"
CORE = DESKTOP / "packages/core/src"


class DesktopBillingContainmentWave45Tests(unittest.TestCase):
    def test_billing_url_requires_first_party_configuration(self):
        source = (UI / "utils/urls.ts").read_text()
        fn = source[source.index("export function getBillingUrl("):]
        for token in ("VITE_FLIND_CLOUD_APP_HOST", "VITE_FLIND_BILLING_URL",
                      'verifyFlindExternalLink(',):
            self.assertIn(token, fn)
        for forbidden in ("getCloudUrlFromRegion(", "posthog_code_usage", "getPostHogUrl("):
            self.assertNotIn(forbidden, fn)

    def test_upgrade_modal_does_not_offer_unconfigured_payment(self):
        source = (UI / "features/billing/UsageLimitModal.tsx").read_text()
        self.assertIn("actionAvailable={verifiedBillingUrl !== null}", source)
        self.assertIn("content.actionLabel && actionAvailable", source)
        self.assertIn("Flind billing is not configured for this installation.", source)
        test = (UI / "features/billing/UsageLimitModal.test.tsx").read_text()
        self.assertIn("actionAvailable={false}", test)
        self.assertIn("onAction).not.toHaveBeenCalled()", test)

    def test_old_pricing_and_credit_proclamations_are_removed(self):
        source = (CORE / "billing/usageLimitContent.ts").read_text()
        self.assertNotIn("PostHog Desktop credit limit", source)
        self.assertNotIn("you only pay for what you use", source)
        self.assertIn("configured usage limit", source)


if __name__ == "__main__":
    unittest.main()
