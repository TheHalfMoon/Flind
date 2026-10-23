"""Scoped Flind logo, invitation and authentication copy guardrails."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "post" + "hog"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PrimaryIdentityTests(unittest.TestCase):
    def test_logo_wrapper_uses_first_party_text(self) -> None:
        source = read("frontend/src/lib/brand/index.tsx")
        self.assertIn("aria-label=\"Flind\"", source)
        self.assertIn("Flind", source)
        self.assertNotIn("<BrandLogo", source)
        self.assertNotIn("import { Logo as BrandLogo }", source)

    def test_auth_header_keeps_navigation_local(self) -> None:
        source = read("frontend/src/scenes/authentication/shared/WelcomeLogo.tsx")
        self.assertIn('to="/"', source)
        self.assertIn('aria-label="Flind home"', source)
        self.assertNotIn(OLD + ".com", source)

    def test_invitation_copy_no_longer_links_elsewhere(self) -> None:
        source = read("frontend/src/scenes/authentication/invite-signup/InviteSignupForm.tsx")
        self.assertIn("on Flind", source)
        self.assertIn("Flind home", source)
        self.assertNotIn(OLD + ".com", source)
        self.assertNotIn("HedgehogJudge", source)

    def test_account_mismatch_copy_is_flind(self) -> None:
        source = read("frontend/src/scenes/authentication/account/AgenticAccountMismatch.tsx")
        self.assertIn("different Flind account", source)


if __name__ == "__main__":
    unittest.main()
