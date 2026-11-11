"""Guard user-visible Flind entrypoints without renaming compatibility internals.

Scope deliberately excludes SDK symbols and wire identifiers that require migrations.
These tests are cheap, dependency-free and must run before every identity-only PR.
"""

from __future__ import annotations

import re
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
    "frontend/src/index.html",
    "posthog/templates/overlays.html",
    "posthog/templates/500.html",
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
        # Rebranding cannot silently rename loaded SDK/protocol modules. The icon set is the exception:
        # it is vendored as the @flind/icons workspace package (rename stage 3, packages/icons).
        self.assertIn(
            "from '@flind/icons'",
            read("frontend/src/scenes/onboarding/welcome/WelcomeAiPanel.tsx"),
        )
        self.assertIn(
            "import { IconArrowRight } from '@flind/icons'",
            read("frontend/src/scenes/onboarding/exit/OnboardingExitModal.tsx"),
        )

    def test_error_page_is_self_contained(self) -> None:
        page = read("posthog/templates/500.html")
        self.assertNotIn("<iframe", page)
        self.assertNotIn("posthog.com", page)
        self.assertIn("Flind is temporarily unavailable", page)

    def test_app_shell_console_has_no_upstream_links(self) -> None:
        shell = read("frontend/src/index.html")
        self.assertNotIn("posthog.com", shell)
        self.assertNotIn("In data we trust", shell)

    def test_debug_warning_uses_flind_name(self) -> None:
        settings = read("posthog/settings/base_variables.py")
        self.assertIn("Flind is running in DEVELOPMENT MODE!", settings)
        self.assertNotIn("PostHog is running in DEVELOPMENT MODE!", settings)


    def test_server_templates_do_not_name_upstream_product(self) -> None:
        # Product name only; code identifiers such as the PostHogHostedSurvey CSS class are allowed.
        # posthog.com links are tracked separately until the docs target is decided.
        name = re.compile(r"PostHog(?![A-Za-z])")
        for base in ("posthog/templates", "ee/templates"):
            root = ROOT / base
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.suffix not in {".html", ".txt", ".md"}:
                    continue
                with self.subTest(file=str(path.relative_to(ROOT))):
                    self.assertIsNone(name.search(path.read_text(encoding="utf-8")))

    def test_auth_md_does_not_claim_open_source(self) -> None:
        self.assertNotIn("open-source", read("posthog/templates/auth_md.md"))

    def test_email_subjects_do_not_name_upstream_product(self) -> None:
        subject = re.compile(r'subject\s*=\s*f?"[^"]*PostHog(?![A-Za-z])')
        for rel in (
            "posthog/tasks/email.py",
            "posthog/tasks/alerts/utils.py",
            "posthog/temporal/proxy_service/common.py",
        ):
            with self.subTest(file=rel):
                self.assertIsNone(subject.search(read(rel)))
    def test_api_errors_do_not_name_upstream_product(self) -> None:
        name = re.compile(r"PostHog(?![A-Za-z])")
        for rel in ("posthog/exceptions.py", "posthog/api/proxy_record.py", "ee/api/billing.py"):
            with self.subTest(file=rel):
                self.assertIsNone(name.search(read(rel)))

    def test_reserved_proxy_domains_are_not_attributed_to_flind(self) -> None:
        # These checks reject the donor's own domains; claiming Flind owns them would be false.
        self.assertIn("This domain is reserved", read("posthog/api/proxy_record.py"))
    def test_core_ui_messages_use_flind(self) -> None:
        # Spot checks on high-traffic UI copy rewritten by the core UI pass.
        for rel, phrase in (
            ("frontend/src/RootErrorBoundary.tsx", "PostHog crashed"),
            ("frontend/src/lib/insights/sharedUtils.ts", "PostHog is busy"),
            ("frontend/src/scenes/settings/organization/InviteModal.tsx", "|| 'PostHog'"),
        ):
            with self.subTest(file=rel):
                self.assertNotIn(phrase, read(rel))
    def test_model_help_text_does_not_name_upstream_product(self) -> None:
        help_text = re.compile(r"help_text\s*=\s*[\"'][^\"']*PostHog(?![A-Za-z])")
        for rel in ("posthog/models/oauth.py", "posthog/models/organization.py", "posthog/models/user.py"):
            with self.subTest(file=rel):
                self.assertIsNone(help_text.search(read(rel)))

    def test_frontend_makes_no_legal_or_custody_claims_for_flind(self) -> None:
        # Flind is self-hosted software, not a contracting party or data custodian.
        claim = re.compile(
            r"(BAA|DPA|agreement|subprocessor)[^.\n]*with Flind|stays with Flind|Flind subprocessors|Flind will update the DPA"
        )
        for path in sorted((ROOT / "frontend" / "src").rglob("*.tsx")) + sorted((ROOT / "frontend" / "src").rglob("*.ts")):
            if ".test." in path.name:
                continue
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertIsNone(claim.search(path.read_text(encoding="utf-8")))

    def test_support_access_setting_refers_to_instance_staff(self) -> None:
        # Behind the CONTROL_SUPPORT_LOGIN flag, so browser E2E cannot reach it; check the copy here.
        text = read("frontend/src/scenes/settings/user/AllowImpersonation.tsx")
        self.assertIn("Staff users of this Flind instance may need to log in as you", text)
        self.assertNotIn("Flind support staff", text)

if __name__ == "__main__":
    unittest.main()
