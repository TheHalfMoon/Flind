"""Active UI docs must resolve only to configured Flind-owned destinations."""
from pathlib import Path
import unittest

FRONT = Path(__file__).resolve().parents[2] / "frontend/src"


def read(relative: str) -> str:
    return (FRONT / relative).read_text(encoding="utf-8")


class HelpLinksWave70Tests(unittest.TestCase):
    def test_product_tour_tooltips_have_no_vendor_urls(self):
        src = read("scenes/product-tours/components/StepSettings.tsx")
        self.assertEqual(src.count("docLink={docsUrl ?? undefined}"), 4)
        self.assertIn("const docsUrl = flindPublicUrl('docs')", src)
        self.assertIn("When set to 'Dynamic', Flind will not attempt", src)
        self.assertNotIn("posthog.com/docs", src)

    def test_paths_help_fails_closed_without_public_site(self):
        src = read("scenes/web-analytics/PathCleaningToggle.tsx")
        self.assertIn("const docsUrl = flindPublicUrl('docs')", src)
        self.assertIn("{docsUrl && (", src)
        self.assertIn("<Link to={docsUrl}>Learn more", src)
        self.assertNotIn("posthog.com/docs", src)

    def test_experiment_docs_have_no_broken_fallback(self):
        src = read("scenes/experiments/ExperimentWizard/ExperimentWizard.tsx")
        self.assertIn("const docsUrl = flindPublicUrl('docs')", src)
        self.assertIn("{docsUrl && (", src)
        self.assertIn("to={docsUrl}", src)
        self.assertNotIn("posthog.com/docs", src)

    def test_shared_link_ownership_guard_is_still_strict(self):
        src = read("lib/flindPublicLinks.ts")
        self.assertIn("url.hostname !== hostname", src)
        self.assertIn("url.protocol !== 'https:'", src)
        self.assertIn("url.port", src)
        self.assertIn("return null", src)

    def test_only_scoped_ui_surfaces_were_rewritten(self):
        for filename in (
            "scenes/product-tours/components/StepSettings.tsx",
            "scenes/web-analytics/PathCleaningToggle.tsx",
            "scenes/experiments/ExperimentWizard/ExperimentWizard.tsx",
        ):
            with self.subTest(filename=filename):
                src = read(filename)
                self.assertNotIn("https://posthog.com/docs", src)
                self.assertIn("flindPublicUrl", src)


if __name__ == "__main__":
    unittest.main()
