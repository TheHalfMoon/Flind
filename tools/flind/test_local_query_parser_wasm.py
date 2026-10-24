"""The Flind query parser is a real vendored local WASM workspace, not an npm registry alias."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "common/hogql_parser/package.json"
DIST = ROOT / "common/hogql_parser/dist"
EXPECTED = {
    "hogql_parser_wasm.cjs": "6e07a914836382396dd5ae48e141bca057b81c149fa14b813bebc805b031e74c",
    "hogql_parser_wasm.js": "c299321cd458d676719baf093ea5bb2e09fd103c4a1e86ed361b7911bc4f7a66",
    "hogql_parser_wasm_browser.js": "42816282c6c5d1e89c96c53243ef3f198677fee78721e2c4a738ab83de47a47b",
    "index.cjs": "2dce8a5de8b9c311c98e5e3859d72157e3ea3852754503274a45712cf4cbd7b9",
    "index.d.ts": "83e73030de5415291f6e9f2cc97080e6e279b964af12217f163e7238bc1209c6",
}


class LocalQueryParserWasmTests(unittest.TestCase):
    def test_compiled_files_are_present_and_match_verified_release(self) -> None:
        for name, digest in EXPECTED.items():
            with self.subTest(file=name):
                path = DIST / name
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_manifest_and_workspace_resolve_locally(self) -> None:
        parser = json.loads(MANIFEST.read_text())
        frontend = json.loads((ROOT / "frontend/package.json").read_text())
        self.assertEqual(parser["name"], "@flind/query-parser")
        self.assertIs(parser["private"], True)
        self.assertEqual(frontend["dependencies"]["@flind/query-parser"], "workspace:*")
        self.assertIn("    - common/hogql_parser\n", (ROOT / "pnpm-workspace.yaml").read_text())
        for field in ("main", "module", "types"):
            self.assertTrue((MANIFEST.parent / parser[field]).is_file(), field)

    def test_frozen_lockfile_points_to_workspace_not_public_registry(self) -> None:
        lock = (ROOT / "pnpm-lock.yaml").read_text()
        self.assertIn("'@flind/query-parser':\n        specifier: workspace:*\n        version: link:../common/hogql_parser", lock)
        self.assertNotIn("'@flind/query-parser@1.3.88':", lock)

    def test_generated_glue_does_not_require_unsafe_eval(self) -> None:
        for name in ("hogql_parser_wasm.cjs", "hogql_parser_wasm.js",
                     "hogql_parser_wasm_browser.js"):
            with self.subTest(glue=name):
                contents = (DIST / name).read_text()
                self.assertNotIn("new Function(", contents)
                self.assertNotIn("DYNAMIC_EXECUTION=0 was set", contents)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for compiled WASM smoke test")
    def test_native_node_runtime_parses_select_one(self) -> None:
        script = (
            'const factory = require(process.argv[1]);'
            'Promise.resolve(factory()).then(parser => {'
            'const result=JSON.parse(parser.parseSelect("SELECT 1"));'
            'if(result.node!=="SelectQuery") throw Error("wrong AST node");'
            '}).catch(err=>{console.error(err);process.exitCode=1});'
        )
        result = subprocess.run(
            ["node", "-e", script, str(DIST / "index.cjs")],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
