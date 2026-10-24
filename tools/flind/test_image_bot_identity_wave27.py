"""Protect Flind's image bot against inherited vendor impersonation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "nodejs/src/ingestion/pipelines/sessionreplay"
BRANCHES = (
    "ml-mirror-image-fetch",
    "ai-research/image-fetch-v4",
)


class ImageBotIdentityWave27Tests(unittest.TestCase):
    def test_shared_flind_bot_identity_has_no_inherited_default(self):
        src = (BASE / "flind-image-bot-identity.ts").read_text()
        self.assertIn("BOT_NAME = 'FlindImageFetcherBot'", src)
        self.assertIn("FLIND_IMAGE_FETCHER_IDENTITY_ORIGIN", src)
        self.assertIn("host.endsWith('.posthog.com')", src)
        self.assertIn("url.protocol !== 'https:'", src)
        self.assertIn("if (!origin)", src)
        self.assertNotIn("https://us.posthog.com", src)
        self.assertNotIn("PostHogImageFetcherBot", src)

    def test_both_lanes_share_identity_and_reject_unsigned_fallback(self):
        for name in BRANCHES:
            base = BASE / name
            with self.subTest(lane=name):
                identity = (base / "request-identity.ts").read_text()
                auth = (base / "web-bot-auth.ts").read_text()
                self.assertIn("flind-image-bot-identity", identity)
                self.assertIn("flindSignatureAgentHeader", auth)
                self.assertIn("flindSignatureAgentHeader()", auth)
                self.assertIn("private readonly agentHeader: string", auth)
                self.assertNotIn("SIGNATURE_AGENT_URL", auth)
                self.assertNotIn("'https://us.posthog.com/'", auth)

    def test_test_fixtures_follow_flind_bot_policy(self):
        for name in BRANCHES:
            base = BASE / name
            for file in ("image-fetcher.test.ts", "configuration-policy.test.ts"):
                source = (base / file).read_text()
                self.assertIn("FlindImageFetcherBot", source)
                self.assertNotIn("PostHogImageFetcherBot", source)
            auth_test = (base / "web-bot-auth.test.ts").read_text()
            self.assertIn("identity.flind.example", auth_test)
            self.assertIn("refuses signing with missing or inherited identity origins", auth_test)


if __name__ == "__main__":
    unittest.main()
