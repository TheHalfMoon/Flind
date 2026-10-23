"""First-party Flind untrusted-content URL gate (static regression)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRUSTED = ROOT / "frontend/src/lib/utils/trustedUrl.ts"


class FirstPartyTrustedUrlTests(unittest.TestCase):
    def test_no_implicit_trust_for_inherited_vendor_domains(self) -> None:
        source = TRUSTED.read_text()
        self.assertIn("isTrustedFlindUrl", source)
        self.assertIn("parsed.origin === window.location.origin", source)
        self.assertNotIn("post" + "hog.com", source)
        self.assertNotIn("isTrustedPost" + "HogUrl", source)

    def test_markdown_and_details_both_use_same_boundary(self) -> None:
        for relative in (
            "frontend/src/lib/lemon-ui/LemonMarkdown/LemonMarkdown.tsx",
            "frontend/src/lib/utils/renderDetailWithLinks.tsx",
        ):
            with self.subTest(file=relative):
                source = (ROOT / relative).read_text()
                self.assertIn("isTrustedFlindUrl(", source)
                self.assertNotIn("isTrustedPost" + "HogUrl", source)

    def test_detail_link_tests_agree_with_new_trust_boundary(self) -> None:
        source = (ROOT / "frontend/src/lib/utils/renderDetailWithLinks.test.tsx").read_text()
        self.assertIn("Flind same-origin", source)
        self.assertIn("inherited provider links as untrusted", source)

    def test_cross_origin_and_port_change_covered_by_frontend_tests(self) -> None:
        source = (ROOT / "frontend/src/lib/utils/trustedUrl.test.ts").read_text()
        self.assertIn("http://localhost:9000", source)
        self.assertIn("https://localhost", source)
        self.assertIn("//evil.example", source)
        self.assertIn("data:image/png", source)


if __name__ == "__main__":
    unittest.main()
