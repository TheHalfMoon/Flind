"""Local first-party UI package identity and built artifact regression."""
from pathlib import Path
import hashlib
import json
import subprocess
import unittest
from tools.flind.check_workspace_links import REPO_ROOT, inspect_packages, load_tracked_package_manifests

PKG = REPO_ROOT / "frontend/flind/lemon-ui"
HASHES = {
    "index.js": "d85d1f9e764479f7d5d19513d984cb09b474c3f5dc82281bc0b80030157f2f26",
    "index.d.ts": "95e01032b717e7b2f278b806ecc3f9d793e55f99258cb8f8878b01b260305ca2",
    "index.css": "24344290ad760c98e874e60ea320bb2ce312e35b6f972247901d9f8408a2b7dc",
    "assets/Inter-QS6Q44GO.woff": "4c1f8a0d5ef1e04d7e14d194a4ef624345e7c7c1cdb4ff61d4552e32a60ac1d0",
    "assets/Inter-YI3GW4KE.woff2": "b8f1c14c5b866e78f8a733e4b6dc07939ced609e89fee2bf4e5261cd6b5ecb23",
}

class LocalUiTests(unittest.TestCase):
    def test_package(self):
        doc = json.loads((PKG / "package.json").read_text())
        self.assertEqual(doc["name"], "@flind/lemon-ui")
        self.assertIs(doc["private"], True)
        self.assertIn("antd", doc["peerDependencies"])
        self.assertFalse((PKG / "pnpm-lock.yaml").exists())

    def test_bundle_hashes(self):
        for name, expected in HASHES.items():
            self.assertEqual(hashlib.sha256((PKG/"dist"/name).read_bytes()).hexdigest(), expected)

    def test_local_lockfile(self):
        lock = (REPO_ROOT/"pnpm-lock.yaml").read_text()
        self.assertEqual(lock.count("'@flind/lemon-ui':"), 19)
        self.assertEqual(lock.count("version: link:../../frontend/flind/lemon-ui"), 19)
        self.assertNotIn("'@flind/lemon-ui@0.0.0':", lock)

    def test_dependency_graph(self):
        data = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
        self.assertTrue(data["workspace_gate_passed"], data)
        self.assertTrue(data["package_identity_gate_passed"], data)
        self.assertEqual(data["remaining_legacy_package_names"], [])

    def test_compiled_js_syntax(self):
        check = subprocess.run(["node", "--check", str(PKG/"dist/index.js")],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_product_manifests_link_locally(self):
        imports = 0
        for path in (REPO_ROOT / "products").glob("*/package.json"):
            data = json.loads(path.read_text())
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                if "@flind/lemon-ui" in data.get(section, {}):
                    self.assertEqual(data[section]["@flind/lemon-ui"], "workspace:*", path)
                    imports += 1
        self.assertEqual(imports, 19)

    def test_stylesheet_font_assets_are_locally_available(self):
        css = (PKG / "dist/index.css").read_text()
        for name in ("Inter-QS6Q44GO.woff", "Inter-YI3GW4KE.woff2"):
            self.assertIn("./assets/" + name, css)
            self.assertTrue((PKG / "dist/assets" / name).is_file())

    def test_build_and_import_aliases_target_moved_source(self):
        self.assertIn("../../../common/esbuilder/utils.mjs", (PKG / "build.mjs").read_text())
        self.assertTrue((REPO_ROOT / "common/esbuilder/utils.mjs").is_file())
        self.assertIn("@flind/lemon-ui", (REPO_ROOT / "tsconfig.json").read_text())
        self.assertIn("<rootDir>/flind/lemon-ui/src", (REPO_ROOT / "frontend/jest.config.ts").read_text())
        self.assertFalse((REPO_ROOT / "frontend/@posthog/lemon-ui").exists())
