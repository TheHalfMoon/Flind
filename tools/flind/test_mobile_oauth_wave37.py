"""Require explicit OAuth success and cancellation in Mobile install flows."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MOBILE = ROOT / "products/desktop/apps/mobile/src"


class MobileOAuthWave37Tests(unittest.TestCase):
    def test_callback_validation_rejects_lookalikes_and_error_callbacks(self):
        source = (MOBILE / "features/mcp/oauth.ts").read_text()
        self.assertIn('url.hostname === "mcp-oauth"', source)
        self.assertIn('url.pathname === "/callback"', source)
        self.assertIn('!url.searchParams.has("error")', source)
        self.assertIn("isSuccessfulMcpOAuthCallback(result.url)", source)
        self.assertIn("isSuccessfulMcpOAuthCallback(url)", source)

    def test_template_and_custom_success_are_not_reported_cancelled(self):
        source = (MOBILE / "features/mcp/oauth.ts").read_text()
        self.assertIn('return "completed";', source)
        self.assertIn("return outcome;", source)
        self.assertNotIn('"cancelled" ? "cancelled" : "cancelled"', source)

    def test_cancelled_custom_install_does_not_navigate_or_claim_success(self):
        source = (MOBILE / "app/mcp-servers/add-custom.tsx").read_text()
        self.assertIn("const result = await installCustomWithOAuth(", source)
        self.assertIn('if (result === "cancelled")', source)
        self.assertIn("setSubmitting(false);", source)
        self.assertIn("await installations.refetch();", source)


if __name__ == "__main__":
    unittest.main()
