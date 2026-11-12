"""Regression checks for error tracking help destinations."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'frontend/src/lib/components/Errors'
FILES = ('Exception/known-exceptions/javascript/load-failed.tsx', 'StackTrace/EmptyStackTrace.tsx', 'FingerprintRecordPartDisplay.tsx')

class ErrorTrackingHelpIsolationTests(unittest.TestCase):
    def test_no_donor_documentation_links(self):
        for relative in FILES:
            with self.subTest(file=relative):
                self.assertNotIn('posthog.com/docs/', (ROOT / relative).read_text(encoding='utf-8'))

    def test_local_help_and_fingerprint_remain(self):
        self.assertIn('CORS configuration', (ROOT / FILES[0]).read_text(encoding='utf-8'))
        self.assertIn('No stacktrace available', (ROOT / FILES[1]).read_text(encoding='utf-8'))
        self.assertIn('renderPartTooltip(part)', (ROOT / FILES[2]).read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()
