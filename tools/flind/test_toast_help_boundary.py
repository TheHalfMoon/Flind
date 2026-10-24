"""Source-only regression: Flind error toast support must not egress to an inherited site."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOAST = ROOT / "frontend/src/lib/lemon-ui/LemonToast/getHelp.ts"
SUPPORT = ROOT / "frontend/src/lib/components/Support/openInAppSupport.ts"
TEST = ROOT / "frontend/src/lib/lemon-ui/LemonToast/getHelp.test.ts"


class FirstPartyErrorHelpTests(unittest.TestCase):
    def test_no_hardcoded_inherited_help_host(self) -> None:
        code = TOAST.read_text()
        self.assertNotIn("post" + "hog.com", code)
        self.assertIn("flindPublicUrl('docs')", code)
        self.assertIn("if (!docsUrl)", code)
        self.assertIn("window.open(target.toString(), '_blank', 'noopener,noreferrer')", code)

    def test_campaign_values_are_url_encoded(self) -> None:
        code = TOAST.read_text()
        self.assertIn("new URL(docsUrl)", code)
        self.assertIn("target.searchParams.set('utm_medium', 'in-product')", code)
        self.assertIn("target.searchParams.set('utm_campaign', utmCampaign)", code)
        self.assertNotIn("utm_campaign=${utmCampaign}", code)

    def test_in_app_support_action_is_preserved(self) -> None:
        code = TOAST.read_text()
        self.assertIn("setGetHelpAction(action: GetHelpAction)", code)
        self.assertIn("getHelpAction()", code)
        self.assertIn("resetGetHelpAction()", code)
        self.assertIn("openSupportOptions(utmCampaign)", SUPPORT.read_text())

    def test_frontend_jest_regressions_exist(self) -> None:
        code = TEST.read_text()
        self.assertIn("openSpy).not.toHaveBeenCalled()", code)
        self.assertIn("widget & error#1", code)
        self.assertIn("noopener,noreferrer", code)
        self.assertIn("setGetHelpAction(customAction)", code)


if __name__ == "__main__":
    unittest.main()
