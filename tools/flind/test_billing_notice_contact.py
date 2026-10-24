"""Flind billing notice must not point customers to another provider's sales inbox."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTICE = ROOT / "frontend/src/layout/navigation/projectNoticeLogic.tsx"


class FlindBillingNoticeContactTests(unittest.TestCase):
    def test_no_inherited_sales_mailbox(self) -> None:
        code = NOTICE.read_text()
        self.assertNotIn("mailto:sales@post" + "hog.com", code)
        self.assertIn("const docsUrl = flindPublicUrl('docs')", code)
        self.assertIn("if (!docsUrl)", code)
        self.assertIn("to: docsUrl", code)

    def test_contact_action_is_not_invented_without_operator_configuration(self) -> None:
        source = NOTICE.read_text()
        beginning = source.index("if (billingAlert.contactSupport)")
        ending = source.index("\n    if (!canAccessBilling)", beginning)
        contact = source[beginning:ending]
        self.assertIn("return undefined", contact)
        self.assertIn("children: 'View support options'", contact)
        self.assertIn("reportBillingAlertActionClicked(billingAlert)", contact)
        self.assertNotIn("mailto:", contact)

    def test_local_billing_navigation_still_exists(self) -> None:
        code = NOTICE.read_text()
        self.assertIn("to: getBillingAlertBillingUrl(billingAlert)", code)
        self.assertIn("urls.organizationBilling(", code)


if __name__ == "__main__":
    unittest.main()
