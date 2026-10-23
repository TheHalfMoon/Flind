"""Static gates for first-party Flind authentication surfaces (not a browser test)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "frontend/src/scenes/authentication"
SCOPED = [
    "account/AccountConnected.tsx",
    "account/credential-review/CredentialReview.tsx",
    "account/credential-review/PartnerAccessChoice.tsx",
    "login/LoginForm.tsx",
    "password-reset/PasswordReset.tsx",
    "shared/loginErrorMessages.tsx",
    "signup/Signup.tsx",
    "vercel/VercelConnect.tsx",
    "verify-email/VerifyEmailForm.tsx",
]
VENDOR = "post" + "hog"


class FlindAuthSurfaceTests(unittest.TestCase):
    def test_scoped_auth_screens_show_only_flind_name(self) -> None:
        for rel in SCOPED:
            with self.subTest(file=rel):
                content = (BASE / rel).read_text()
                self.assertNotIn("Post" + "Hog", content)

    def test_scoped_auth_screens_do_not_link_to_other_vendor(self) -> None:
        for rel in SCOPED:
            with self.subTest(file=rel):
                content = (BASE / rel).read_text()
                self.assertNotIn("https://" + VENDOR + ".com", content)

    def test_login_does_not_claim_unverified_customer_count(self) -> None:
        content = (BASE / "login/LoginForm.tsx").read_text()
        self.assertNotIn("500,000+ teams", content)
        self.assertIn("New to Flind?", content)

    def test_legacy_mascots_removed_from_auth_gates(self) -> None:
        for rel in ("login/LoginForm.tsx", "verify-email/VerifyEmailForm.tsx", "account/credential-review/CredentialReview.tsx"):
            with self.subTest(file=rel):
                content = (BASE / rel).read_text()
                self.assertIn("Logomark", content)
                self.assertNotIn("pngHoggie", content)
                self.assertNotIn("Hedgehog", content)

    def test_no_invented_terms_policy_links(self) -> None:
        signup = (BASE / "signup/Signup.tsx").read_text()
        self.assertNotIn(VENDOR + ".com/terms", signup)
        self.assertNotIn(VENDOR + ".com/privacy", signup)
        self.assertIn("Flind workspace administrator", signup)

    def test_sso_and_password_help_remain_actionable(self) -> None:
        for rel in ("password-reset/PasswordReset.tsx", "shared/loginErrorMessages.tsx"):
            with self.subTest(file=rel):
                content = (BASE / rel).read_text()
                self.assertIn("administrator", content.lower())
                self.assertNotIn("https://" + VENDOR + ".com", content)


if __name__ == "__main__":
    unittest.main()
