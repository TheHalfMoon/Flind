"""Prevent compiled local-studio development credentials and legacy login branding."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'products/desktop/apps/mobilehog/src'


class MobileStudioLocalLoginWave31Tests(unittest.TestCase):
    def test_no_bundled_development_login_identity(self):
        source=(BASE/'config.ts').read_text()
        self.assertNotIn('export const DEV_EMAIL',source)
        self.assertNotIn('export const DEV_PASSWORD',source)

    def test_local_login_requires_user_entry_in_development_only(self):
        source=(BASE/'app/login.tsx').read_text()
        self.assertIn('{__DEV__ ? (',source)
        self.assertIn('onChangeText={setLocalEmail}',source)
        self.assertIn('onChangeText={setLocalPassphrase}',source)
        self.assertIn('secureTextEntry',source)
        self.assertIn('login(localEmail.trim(), localPassphrase)',source)
        self.assertIn('setLocalPassphrase("")',source)
        self.assertNotIn('login(DEV_EMAIL, DEV_PASSWORD)',source)

    def test_user_facing_first_party_identity(self):
        source=(BASE/'app/login.tsx').read_text()
        self.assertIn('>Flind Studio</Text>',source)
        self.assertIn('Sign in to local Flind',source)
        self.assertNotIn('>PostHog</Text>',source)


if __name__=='__main__':
    unittest.main()
