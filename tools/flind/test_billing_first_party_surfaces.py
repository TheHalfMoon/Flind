"""Flind billing surfaces must not advertise inherited external sales contacts."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BILLING = ROOT / "frontend/src/scenes/billing/Billing.tsx"
CREDIT = ROOT / "frontend/src/scenes/billing/CreditCTAHero.tsx"


class FlindBillingFirstPartyTests(unittest.TestCase):
    def test_billing_error_has_no_upstream_sales_email(self) -> None:
        source = BILLING.read_text()
        self.assertNotIn("mailto:sales@post" + "hog.com", source)
        self.assertIn("const docsUrl = flindPublicUrl('docs')", source)
        self.assertIn("contact your Flind workspace administrator", source)

    def test_in_app_bug_reporting_is_preserved(self) -> None:
        source = BILLING.read_text()
        self.assertIn("openSupportForm({ kind: 'bug', billing_issue: true })", source)
        self.assertIn("<Link to={docsUrl} target=", source)

    def test_credit_card_does_not_promote_unsupported_enterprise_offer(self) -> None:
        source = CREDIT.read_text()
        self.assertNotIn("mailto:sales@post" + "hog.com", source)
        self.assertNotIn("private Slack channel", source)
        self.assertNotIn("free merch", source)
        self.assertIn("creditOverview.status === 'none' && docsUrl &&", source)
        self.assertIn("<LemonButton type=\"secondary\" to={docsUrl}>", source)

    def test_existing_billing_and_credit_actions_unchanged(self) -> None:
        source = CREDIT.read_text()
        self.assertIn("showPurchaseCreditsModal", source)
        self.assertIn("PurchaseCreditsModal", source)
        self.assertIn("toggleCreditCTAHeroDismissed", source)
        self.assertIn("creditOverview.invoice_url", source)


if __name__ == "__main__":
    unittest.main()
