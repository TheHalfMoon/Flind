"""Regression guard for shared/exported pages independent of upstream marketing endpoints."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / "frontend/src/exporter/Exporter.tsx"


class ExporterBrandWave19Tests(unittest.TestCase):
    def test_shared_scene_titles_are_flind_branded(self):
        source = EXPORTER.read_text()
        self.assertEqual(source.count('${baseTitle} • Flind'), 3)
        self.assertNotIn('${baseTitle} • PostHog', source)

    def test_no_inherited_marketing_destinations_in_shared_exports(self):
        source = EXPORTER.read_text()
        self.assertNotIn('https://posthog.com', source)
        self.assertNotIn('utm_campaign=shared-', source)
        self.assertNotIn("import { Link } from 'lib/lemon-ui/Link'", source)

    def test_logo_and_credits_remain_local(self):
        source = EXPORTER.read_text()
        self.assertGreaterEqual(source.count('<Logo size="xs" />'), 4)
        self.assertIn('Flind — open-source product analytics', source)
        self.assertNotIn('PostHog — open-source product analytics', source)

    def test_existing_embed_message_protocol_preserved(self):
        source = EXPORTER.read_text()
        # An embedded client can depend on this existing wire event. A protocol
        # migration needs its own cross-frame compatibility tests.
        self.assertIn("event: 'posthog:dimensions'", source)


if __name__ == "__main__":
    unittest.main()
