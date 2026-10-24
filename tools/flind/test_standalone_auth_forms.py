"""Legacy standalone Django/webpack form entrypoints stay Flind and same-origin."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ("frontend/src/layout.html", "frontend/src/layout.ejs")
CSS = "frontend/public/flind-form-foundation.min.css"
LICENSE = "frontend/public/flind-form-foundation.LICENSE"


class FlindStandaloneFormsTests(unittest.TestCase):
    def test_standalone_auth_page_has_flind_identity(self) -> None:
        for file in PAGES:
            with self.subTest(file=file):
                source = (ROOT / file).read_text()
                self.assertIn("<title>Flind</title>", source)
                self.assertNotIn("<title>Post" + "Hog</title>", source)

    def test_inherited_analytics_loader_is_disabled_without_local_token(self) -> None:
        for file in PAGES:
            with self.subTest(file=file):
                source = (ROOT / file).read_text()
                guard = "{% if not opt_out_capture and js_posthog_api_key %}"
                start = source.index(guard)
                self.assertGreater(source.index("posthog.init(posthogJSApiKey", start), start)
                self.assertGreater(source.index("{% endif %}", start), source.index("posthog.init(posthogJSApiKey", start))
                self.assertEqual(source.count(guard), 1)

    def test_legacy_cloud_sdk_asset_prefix_is_not_used(self) -> None:
        for file in PAGES:
            with self.subTest(file=file):
                source = (ROOT / file).read_text()
                self.assertIn('window.location.origin', source)
                self.assertIn("/static/array.js", source)
                self.assertNotIn(".i.post" + "hog.com", source)
                self.assertNotIn("static/1/array.js", source)

    def test_bootstrap_css_is_bundled_locally_with_vendor_license(self) -> None:
        css = ROOT / CSS
        license_file = ROOT / LICENSE
        self.assertGreater(css.stat().st_size, 50_000)
        self.assertIn("Bootstrap", css.read_text(errors="ignore")[:500])
        self.assertIn("MIT License", license_file.read_text())
        for file in PAGES:
            with self.subTest(file=file):
                source = (ROOT / file).read_text()
                self.assertIn("/flind-form-foundation.min.css", source)
                self.assertNotIn("stackpath.bootstrapcdn.com", source)

    def test_no_unsigned_remote_css_in_legacy_auth_entrypoints(self) -> None:
        for file in PAGES:
            with self.subTest(file=file):
                source = (ROOT / file).read_text()
                self.assertNotIn('href="http', source)
                self.assertNotIn("Trying to make changes here? LOL", source)


if __name__ == "__main__":
    unittest.main()
