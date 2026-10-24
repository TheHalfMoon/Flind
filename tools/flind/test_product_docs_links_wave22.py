"""Fail-closed documentation links in product manifests and their generated consumers.

The build-products generator is not required for this dependency-free source
regression; an actual frontend generation/build still needs separate proof.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_DOC = re.compile(r"docsHref\s*:\s*['\"]https?://(?:www\.)?posthog\.com/docs")


class ProductDocumentationWave22Tests(unittest.TestCase):
    def test_source_manifests_never_advertise_upstream_docs(self):
        manifests = sorted((ROOT / "products").glob("*/manifest.tsx"))
        self.assertGreaterEqual(len(manifests), 20)
        for path in manifests:
            with self.subTest(manifest=path.name, product=path.parent.name):
                self.assertNotRegex(path.read_text(), UPSTREAM_DOC)

    def test_generated_product_configuration_matches_source_boundary(self):
        # Both checked-in generated output and source-of-truth manifests must
        # be migrated together; changing only one gets reverted on regeneration.
        product = (ROOT / "frontend/src/products.tsx").read_text()
        scenes = (ROOT / "frontend/src/scenes/scenes.ts").read_text()
        self.assertNotRegex(product, UPSTREAM_DOC)
        self.assertNotRegex(scenes, UPSTREAM_DOC)
        self.assertIn("...productConfiguration,", scenes)

    def test_sidebar_contract_no_longer_requires_other_vendors_docs(self):
        source = (ROOT / "frontend/src/layout/panel-layout/sidebarProductMeta.ts").read_text()
        tests = (ROOT / "frontend/src/layout/panel-layout/sidebarProductMeta.test.ts").read_text()
        self.assertIn("docsHref: sceneConfig?.docsHref", source)
        self.assertNotIn("SIDEBAR_PRODUCTS_WITHOUT_DOCS", source)
        self.assertNotIn("SIDEBAR_PRODUCTS_WITHOUT_DOCS", tests)
        self.assertIn("expect(docsHref).toBeUndefined()", tests)
        self.assertNotIn("toMatch(/^https:", tests)


if __name__ == "__main__":
    unittest.main()
