from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] / "frontend/src"


class SupportWave71Tests(unittest.TestCase):
    def test_no_inherited_email_fallback(self):
        data = (ROOT / "lib/lemon-ui/LemonToast/LemonToast.tsx").read_text()
        self.assertIn("ToastButton | undefined = supportMailto", data)
        self.assertNotIn("mailto:supportreply@", data)

    def test_owned_mailbox_only(self):
        data = (ROOT / "lib/flindSupportMailto.ts").read_text()
        self.assertIn("VITE_FLIND_SUPPORT_EMAIL_DOMAIN", data)
        self.assertIn("match[2].toLowerCase() !== domain", data)

    def test_linkification_remains_same_origin(self):
        data = (ROOT / "lib/utils/renderDetailWithLinks.tsx").read_text()
        self.assertIn("isTrustedFlindUrl(part)", data)


if __name__ == "__main__":
    unittest.main()
