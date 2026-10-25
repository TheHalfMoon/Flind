"""No inherited vendor docs are presented by scoped, active Flind UI flows."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
F = ROOT / "frontend/src"


def source(path: str) -> str:
    return (F / path).read_text(encoding="utf-8")


class OwnedDocsWave69Tests(unittest.TestCase):
    def test_translations_only_show_owned_help_if_configured(self):
        data = source("scenes/product-tours/editor/TranslationsPanel.tsx")
        self.assertIn("const docsUrl = flindPublicUrl('docs')", data)
        self.assertEqual(data.count("{docsUrl && ("), 2)
        self.assertEqual(data.count("to={docsUrl}"), 2)
        self.assertNotIn("posthog.com/docs", data)
        self.assertIn("Add translations to this {entityKeyword}.", data)

    def test_web_analytics_warning_is_actionable_without_offsite_docs(self):
        data = source("scenes/web-analytics/WebAnalyticsHealthCheck.tsx")
        self.assertIn("const docsUrl = flindPublicUrl('docs')", data)
        self.assertIn("include a valid <code>$session_id</code>", data)
        self.assertIn("{docsUrl && (", data)
        self.assertIn("to={docsUrl}", data)
        self.assertNotIn("posthog.com/docs", data)

    def test_web_analytics_live_count_has_no_legacy_link_default(self):
        data = source("scenes/web-analytics/WebAnalyticsHeaderButtons.tsx")
        child = source("lib/components/LiveUserCount/LiveUserCount.tsx")
        self.assertIn("const docsUrl = flindPublicUrl('docs')", data)
        self.assertIn("docLink={docsUrl ?? undefined}", data)
        self.assertIn("docLink?: string", child)
        self.assertNotIn("posthog.com/docs", data)

    def test_fail_closed_public_docs_source_remains_same_origin_https(self):
        data = source("lib/flindPublicLinks.ts")
        self.assertIn("url.hostname !== hostname", data)
        self.assertIn("url.protocol !== 'https:'", data)
        self.assertIn("return null", data)

    def test_no_global_legal_or_package_brand_replacement(self):
        for path in (
            "scenes/product-tours/editor/TranslationsPanel.tsx",
            "scenes/web-analytics/WebAnalyticsHealthCheck.tsx",
            "scenes/web-analytics/WebAnalyticsHeaderButtons.tsx",
        ):
            with self.subTest(path=path):
                data = source(path)
                self.assertNotIn("posthog.com/docs", data)
                self.assertIn("flindPublicUrl", data)


if __name__ == "__main__":
    unittest.main()
