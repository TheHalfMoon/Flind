"""Scoped regression guard for live Flind help destinations."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    'account': 'frontend/src/lib/components/Account/AccountMenu.tsx',
    'previews': 'frontend/src/lib/components/FeaturePreviews/FeaturePreviews.tsx',
    'hogql': 'frontend/src/lib/components/HogQLEditor/HogQLEditor.tsx',
    'script': 'frontend/src/lib/components/Errors/Exception/known-exceptions/javascript/script-error.tsx',
    'syntax': 'frontend/src/lib/components/Errors/Exception/known-exceptions/javascript/syntax-error.tsx',
    'promise': 'frontend/src/lib/components/Errors/Exception/known-exceptions/javascript/non-error-promise-rejection.tsx',
    'react': 'frontend/src/lib/components/Errors/Exception/known-exceptions/javascript/react-minified-error.tsx',
    'frames': 'frontend/src/lib/components/Errors/Frame/CollapsibleFrameHeader.tsx',
}
SOURCES = {name: (ROOT / path).read_text(encoding='utf-8') for name, path in FILES.items()}
DONOR = re.compile(r'https?://(?:[a-z0-9-]+\.)*posthog\.com\b', re.I)


class LiveHelpIsolationTests(unittest.TestCase):
    def test_no_donor_host_in_scoped_live_sources(self):
        for name, source in SOURCES.items():
            with self.subTest(name=name):
                self.assertIsNone(DONOR.search(source))
                self.assertNotIn('npx @posthog/wizard', source)

    def test_core_actions_and_guidance_remain(self):
        self.assertIn('<ThemeMenu />', SOURCES['account'])
        self.assertIn('Feature previews', SOURCES['account'])
        self.assertNotIn('whats-new-button', SOURCES['account'])
        self.assertIn('hasPosthogJsFailedToLoadFeaturePreviews()', SOURCES['previews'])
        self.assertIn('reverse proxy on your own domain', SOURCES['previews'])
        self.assertIn('Update SQL expression', SOURCES['hogql'])
        self.assertIn('showBreakdownLabelHint', SOURCES['hogql'])

    def test_error_help_and_independent_react_reference_remain(self):
        for name in ('script', 'syntax', 'promise', 'react'):
            with self.subTest(name=name):
                self.assertIn('defineKnownException({', SOURCES[name])
                self.assertIn('<KnownExceptionBanner>', SOURCES[name])
        self.assertIn('https://react.dev/errors/', SOURCES['react'])
        self.assertIn('cross-origin', SOURCES['script'])
        self.assertIn('could not parse the script', SOURCES['syntax'])
        self.assertIn('Reject with an Error instance', SOURCES['promise'])
        self.assertIn('FrameWarningIcon', SOURCES['frames'])
        self.assertIn('resolveFailure={resolve_failure}', SOURCES['frames'])
        self.assertNotIn('SYMBOL_SETS_DOC_LINK', SOURCES['frames'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
