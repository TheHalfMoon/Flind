"""Guard user-visible Flind entrypoints without renaming compatibility internals.

Scope deliberately excludes SDK symbols and wire identifiers that require migrations.
These tests are cheap, dependency-free and must run before every identity-only PR.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

BRANDED_FILES = [
    "frontend/src/scenes/onboarding/welcome/OnboardingWelcome.tsx",
    "frontend/src/scenes/onboarding/welcome/WelcomeAiPanel.tsx",
    "frontend/src/scenes/onboarding/welcome/WelcomeWizardCallout.tsx",
    "frontend/src/scenes/onboarding/exit/OnboardingExitModal.tsx",
    "frontend/src/scenes/onboarding/OnboardingInviteTeammates.tsx",
    "frontend/src/layout/panel-layout/sidebarProductMeta.ts",
    "frontend/src/layout/navigation/Breadcrumbs/breadcrumbsLogic.tsx",
    "frontend/src/scenes/instance/SystemStatus/index.tsx",
    "posthog/templates/email/base.html",
    "posthog/templates/email/invite.html",
    "posthog/templates/email/delegation_invite.html",
]

EMAIL_FILES = [
    "posthog/templates/email/base.html",
    "posthog/templates/email/invite.html",
    "posthog/templates/email/delegation_invite.html",
]


def read(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


class FlindUserFacingBrandTests(unittest.TestCase):
    def test_scoped_surfaces_have_no_upstream_product_name(self) -> None:
        for rel in BRANDED_FILES:
            with self.subTest(file=rel):
                self.assertNotIn("PostHog", read(rel))

    def test_invite_emails_do_not_link_to_upstream_saas(self) -> None:
        for rel in EMAIL_FILES:
            with self.subTest(file=rel):
                self.assertNotIn("https://posthog.com", read(rel))

    def test_invitation_mail_preserves_dynamic_links(self) -> None:
        self.assertIn('href="{{ invite }}"', read("posthog/templates/email/invite.html"))
        self.assertIn('href="{{ invite }}"', read("posthog/templates/email/delegation_invite.html"))
        self.assertIn('href="{% absolute_uri %}"', read("posthog/templates/email/base.html"))

    def test_delegation_subject_matches_preview(self) -> None:
        modal = read("frontend/src/scenes/onboarding/exit/OnboardingExitModal.tsx")
        email = read("posthog/templates/email/delegation_invite.html")
        phrase = "asked you to finish setting up Flind for"
        self.assertIn(phrase, modal)
        self.assertIn(phrase, email)

    def test_legacy_mascots_not_present_in_selected_screens(self) -> None:
        for rel in [
            "frontend/src/scenes/onboarding/welcome/WelcomeAiPanel.tsx",
            "frontend/src/scenes/onboarding/welcome/WelcomeWizardCallout.tsx",
            "frontend/src/scenes/onboarding/exit/OnboardingExitModal.tsx",
        ]:
            with self.subTest(file=rel):
                self.assertNotIn("Hedgehog", read(rel))
                self.assertNotIn("WizardHog", read(rel))
                self.assertNotIn("pngHoggie", read(rel))

    def test_email_header_uses_flind_not_old_image(self) -> None:
        html = read("posthog/templates/email/base.html")
        self.assertIn('<span class="logo">Flind</span>', html)
        self.assertNotIn("posthog-logo.png", html)

    def test_compatibility_imports_remain_intact(self) -> None:
        # Rebranding cannot silently rename loaded SDK/protocol modules.
        self.assertIn(
            "from '@posthog/icons'",
            read("frontend/src/scenes/onboarding/welcome/WelcomeAiPanel.tsx"),
        )
        self.assertIn(
            "import { IconArrowRight } from '@posthog/icons'",
            read("frontend/src/scenes/onboarding/exit/OnboardingExitModal.tsx"),
        )


if __name__ == "__main__":
    unittest.main()
