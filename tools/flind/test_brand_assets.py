"""Source-backed tests for Flind app icons and compatibility aliases."""
from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend/public"
PNG_SIZES = {
    "icons/favicon-16x16.png": (16, 16),
    "icons/favicon-32x32.png": (32, 32),
    "icons/apple-touch-icon.png": (180, 180),
    "icons/android-chrome-192x192.png": (192, 192),
    "icons/android-chrome-512x512.png": (512, 512),
    "flind-logo.png": (320, 56),
}


class FlindBrandAssetTests(unittest.TestCase):
    def test_real_png_headers_and_dimensions(self) -> None:
        for name, dimensions in PNG_SIZES.items():
            with self.subTest(asset=name):
                payload = (PUBLIC / name).read_bytes()
                self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(struct.unpack(">II", payload[16:24]), dimensions)
                self.assertGreater(len(payload), 100)

    def test_icos_contain_real_icon_header(self) -> None:
        for name in ("favicon.ico", "favicon-dev.ico"):
            with self.subTest(asset=name):
                payload = (PUBLIC / "icons" / name).read_bytes()
                self.assertEqual(payload[:4], b"\x00\x00\x01\x00")
                self.assertGreater(int.from_bytes(payload[4:6], "little"), 0)

    def test_primary_svg_icon_and_logo_are_flind_owned(self) -> None:
        for filename in ("flind-icon.svg", "flind-logo.svg"):
            with self.subTest(filename=filename):
                root = ElementTree.fromstring((PUBLIC / filename).read_text())
                self.assertEqual(root.attrib.get("aria-label"), "Flind")
                self.assertNotIn("posthog", (PUBLIC / filename).read_text().lower())

    def test_legacy_url_aliases_show_the_same_new_flind_artwork(self) -> None:
        for ext in ("svg", "png"):
            with self.subTest(extension=ext):
                self.assertEqual(
                    (PUBLIC / f"flind-logo.{ext}").read_bytes(),
                    (PUBLIC / f"posthog-logo.{ext}").read_bytes(),
                )
        self.assertEqual((PUBLIC / "flind-icon.svg").read_bytes(), (PUBLIC / "posthog-icon.svg").read_bytes())

    def test_pwa_icons_are_current_flind_assets(self) -> None:
        manifest = json.loads((PUBLIC / "site.webmanifest").read_text())
        self.assertEqual(manifest["name"], "Flind")
        self.assertEqual(manifest["short_name"], "Flind")
        self.assertEqual(manifest["theme_color"], "#202936")
        for icon in manifest["icons"]:
            self.assertIn("v=2026-10-24", icon["src"])
            self.assertTrue((PUBLIC / icon["src"].split("?")[0].removeprefix("/static/")).is_file())

    def test_html_links_use_new_cache_version(self) -> None:
        template = (ROOT / "posthog/templates/head.html").read_text()
        self.assertIn("/static/icons/favicon.ico?v=2026-10-24", template)
        self.assertIn("/static/icons/safari-pinned-tab.svg?v=2026-10-24", template)
        self.assertNotIn("v=2026-07-07", template)
        scene = (ROOT / "frontend/src/scenes/experiments/experimentResultsNotificationLogic.ts").read_text()
        self.assertIn("/static/flind-icon.svg", scene)


if __name__ == "__main__":
    unittest.main()
