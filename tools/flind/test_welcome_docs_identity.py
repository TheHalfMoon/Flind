"""Flind welcome cards never navigate to an inherited provider's documentation."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANDING = ROOT / "frontend/src/scenes/welcome/productBranding.ts"
FLAGSHIP = ROOT / "frontend/src/scenes/welcome/cards/FlagshipProductsCard.tsx"
IN_USE = ROOT / "frontend/src/scenes/welcome/cards/ProductsInUseCard.tsx"
NOTICE = ROOT / "frontend/src/layout/navigation/projectNoticeLogic.tsx"


class FirstPartyWelcomeDocsTests(unittest.TestCase):
    def test_product_branding_never_supplies_inherited_docs_host(self) -> None:
        source = BRANDING.read_text()
        self.assertNotIn("https://post" + "hog.com", source)
        self.assertEqual(source.count("docsHref: flindPublicUrl('docs') ?? ''"), 10)
        self.assertIn("brandingForProduct", source)

    def test_all_welcome_surfaces_guard_unconfigured_docs_links(self) -> None:
        for path in (FLAGSHIP, IN_USE, NOTICE):
            with self.subTest(path=path.name):
                source = path.read_text()
                self.assertIn("meta.docsHref ?", source)
                self.assertIn("to={meta.docsHref}", source)
                self.assertNotIn("https://post" + "hog.com", source)

    def test_first_party_welcome_identity(self) -> None:
        source = FLAGSHIP.read_text()
        self.assertIn("What you get with Flind", source)
        self.assertNotIn("What you get with Post" + "Hog", source)
        notice = NOTICE.read_text()
        self.assertIn("Welcome to Flind!", notice)
        self.assertNotIn("Welcome to Post" + "Hog!", notice)

    def test_product_fallback_has_no_external_navigation(self) -> None:
        branding = BRANDING.read_text()
        self.assertIn("FALLBACK_BRANDING", branding)
        self.assertIn("docsHref: flindPublicUrl('docs') ?? ''", branding)
        self.assertIn("className={cardClass}", FLAGSHIP.read_text())
        self.assertIn("Your team’s active Flind products", IN_USE.read_text())


if __name__ == "__main__":
    unittest.main()
