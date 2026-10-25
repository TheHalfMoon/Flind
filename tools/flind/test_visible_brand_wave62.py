"""Guard active first-party Flind UI identity and safe help-link defaults.

These focused source contracts stay runnable without installing the full
inherited frontend dependency graph. TS/TSX syntax is checked separately.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend/src/lib"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8")


class VisibleFlindBrandWave62Tests(unittest.TestCase):
    def test_system_annotation_badge_is_flind(self):
        text = read("components/AnnotationsOverlay/AnnotationsOverlay.tsx")
        self.assertIn('content="Flind"', text)
        self.assertNotIn('content="PostHog"', text)

    def test_core_filter_badge_has_neutral_icon_and_flind_copy(self):
        text = read("components/TaxonomicFilter/menu/VerificationBadge.tsx")
        self.assertIn("{isCore ? 'Flind' : 'Verified'}", text)
        self.assertIn("Built into Flind.", text)
        self.assertIn("<IconBadge className=", text)
        self.assertNotIn("<IconLogomark", text)
        self.assertNotIn("PostHog", text)

    def test_captured_exception_fallback_is_first_party(self):
        text = read("components/Errors/ErrorDisplay.tsx")
        self.assertIn("'Flind'", text)
        self.assertNotIn("'PostHog'", text)

    def test_system_and_impersonated_audit_actors_have_neutral_names(self):
        text = read("components/ActivityLog/humanizeActivity.tsx")
        tests = read("components/ActivityLog/humanizeActivity.test.tsx")
        self.assertIn("return 'Flind'", text)
        self.assertIn("return `Support (as", text)
        self.assertIn("name: logItem.was_impersonated", text)
        self.assertNotIn("PostHog Support", text)
        self.assertIn("Support (as Ada Lovelace)", tests)
        self.assertIn("results[0].email", tests)

    def test_help_link_is_hidden_without_verified_flind_docs(self):
        text = read("introductions/GroupsIntroductionOption.tsx")
        url_guard = read("flindPublicLinks.ts")
        self.assertIn("flindPublicUrl('docs')", text)
        self.assertIn("{docsUrl && (", text)
        self.assertIn("to={docsUrl}", text)
        self.assertNotIn("posthog.com", text)
        self.assertIn("url.hostname !== hostname", url_guard)
        self.assertIn("url.protocol !== 'https:'", url_guard)

    def test_only_scoped_active_ui_surfaces_changed(self):
        # Attribution notices, test fixtures, protocol headers, and legacy
        # migrations must not be swept up in indiscriminate replacements.
        for path in [
            "components/AnnotationsOverlay/AnnotationsOverlay.tsx",
            "components/TaxonomicFilter/menu/VerificationBadge.tsx",
            "components/Errors/ErrorDisplay.tsx",
            "introductions/GroupsIntroductionOption.tsx",
        ]:
            with self.subTest(path=path):
                self.assertNotIn("PostHog Cloud", read(path))


if __name__ == "__main__":
    unittest.main()
