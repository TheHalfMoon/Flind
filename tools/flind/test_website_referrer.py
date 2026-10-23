"""Guard the Flind public-site referrer trust boundary."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FlindWebsiteReferrerTests(unittest.TestCase):
    def test_no_inherited_marketing_site_is_trusted(self):
        source = (ROOT / "frontend/src/scenes/authentication/shared/arrivedFromWebsiteLogic.ts").read_text()
        self.assertIn("VITE_FLIND_WEBSITE_HOST", source)
        self.assertIn("url.protocol === 'https:'", source)
        self.assertIn("url.hostname === websiteHostname", source)
        self.assertNotIn("post" + "hog.com", source)

    def test_fixture_uses_first_party_fake_domain(self):
        source = (ROOT / "frontend/src/scenes/authentication/shared/authReferrer.mock.ts").read_text()
        self.assertIn("flind.example", source)
        self.assertNotIn("post" + "hog.com", source)

    def test_referrer_cases_are_explicit_and_hostile_origins_rejected(self):
        source = (ROOT / "frontend/src/scenes/authentication/shared/arrivedFromWebsiteLogic.test.ts").read_text()
        self.assertIn("flind.example.phishing.example/", source)
        self.assertIn("has no trusted marketing website", source)
        self.assertNotIn("post" + "hog.com", source)


if __name__ == "__main__":
    unittest.main()
