"""Ensure Desktop marketing/legal/support links cannot fall back to donor hosts."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
SHARED=ROOT/"products/desktop/packages/shared/src/links.ts"
UI=ROOT/"products/desktop/packages/ui/src"


class DesktopPublicLinksWave41Tests(unittest.TestCase):
    def test_only_official_dependency_installation_links_are_static(self):
        source=SHARED.read_text()
        self.assertIn('https://cli.github.com/',source)
        self.assertIn('https://git-scm.com/downloads',source)
        for forbidden in ('posthog.com','discord.gg','talkToHuman:','privacy:','website:','docs:','discord:'):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden,source)

    def test_first_party_link_guards_are_explicit(self):
        source=(UI/"shell/flindExternalLinks.ts").read_text()
        for token in (
            'parsed.protocol !== "https:"',
            'parsed.hostname.toLowerCase() !== expected',
            'parsed.username',
            'parsed.password',
            'parsed.port',
            'VITE_FLIND_WEBSITE_HOST',
            'VITE_FLIND_PRIVACY_URL',
            'VITE_FLIND_SUPPORT_URL',
        ):
            with self.subTest(token=token):
                self.assertIn(token,source)

    def test_no_old_public_link_fields_in_desktop_ui(self):
        for path in UI.rglob("*"):
            if path.suffix not in (".ts",".tsx") or path.name.endswith(".test.ts") or path.name.endswith(".test.tsx"):
                continue
            contents=path.read_text()
            for key in ("discord","docs","privacy","talkToHuman","website"):
                with self.subTest(path=str(path),key=key):
                    self.assertNotIn("EXTERNAL_LINKS."+key,contents)

    def test_support_hidden_unless_first_party_url_configured(self):
        app=(UI/"shell/App.tsx").read_text()
        self.assertIn('flindExternalUrl("support")',app)
        self.assertIn('flindExternalUrl("community")',app)
        self.assertIn('onOpenSupport={openSupport}',app)
        self.assertIn('onOpenSupport={openCommunity}',app)
        onboarding=(UI/"features/onboarding/components/OnboardingFlow.tsx").read_text()
        self.assertIn('{onOpenSupport && (',onboarding)
        consent=(UI/"features/consent/ConsentScreen.tsx").read_text()
        self.assertIn('{onOpenSupport && (',consent)
        menu=(UI/"features/sidebar/components/ProjectSwitcher.tsx").read_text()
        for key in ("community","privacy","website"):
            self.assertIn('flindExternalUrl("'+key+'")',menu)
        layout=(UI/"primitives/FullScreenLayout.tsx").read_text()
        self.assertIn('{onOpenSupport && (',layout)
        channel=(UI/"features/canvas/components/ChannelIntro.tsx").read_text()
        self.assertIn('flindExternalUrl("docs")',channel)
        self.assertIn('{docsUrl && (',channel)


if __name__=="__main__":
    unittest.main()
