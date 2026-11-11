import json
from pathlib import Path
import tempfile
import unittest
import warnings
from zipfile import ZipFile
from flind_toolbar_zip_integrity import verify_archive


class ZipIntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.archive = root / "chrome.zip"
        self.icon = root / "icon.png"
        self.icon.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"0" * 8 + (128).to_bytes(4, "big") * 2)
        self.manifest = {"name": "Flind", "icons": {"128": "icons/flind-128x128.png"}, "action": {"default_icon": {"128": "icons/flind-128x128.png"}}}

    def make(self, *, manifest=None, icon=None, duplicate=False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.archive, "w") as z:
                z.writestr("manifest.json", json.dumps(self.manifest if manifest is None else manifest))
                z.writestr("icons/flind-128x128.png", self.icon.read_bytes() if icon is None else icon)
                if duplicate:
                    z.writestr("manifest.json", json.dumps(self.manifest))

    def test_good_zip(self):
        self.make()
        verify_archive(self.archive, self.icon)

    def test_external_hosts_denied(self):
        self.make(manifest=dict(self.manifest, externally_connectable={"matches": ["https://example.org/*"]}))
        with self.assertRaisesRegex(ValueError, "External websites"):
            verify_archive(self.archive, self.icon)

    def test_modified_icon_denied(self):
        self.make(icon=b"bad")
        with self.assertRaisesRegex(ValueError, "differs"):
            verify_archive(self.archive, self.icon)

    def test_duplicate_manifest_denied(self):
        self.make(duplicate=True)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            verify_archive(self.archive, self.icon)

    def test_missing_manifest_denied(self):
        with ZipFile(self.archive, "w") as z:
            z.writestr("icons/flind-128x128.png", self.icon.read_bytes())
        with self.assertRaisesRegex(ValueError, "exactly one"):
            verify_archive(self.archive, self.icon)
