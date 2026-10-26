#!/usr/bin/env python3
"""Regression subset for the founder's Flind-only first-party identity rule.

Does NOT imply a green full source or release gate. Runtime identifiers migrate
under separately qualified Django/API/SDK E2E; legal notices are retained.
"""
from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
LEGACY = "post" + "hog"
PRIVATE_FIRST_PARTY = (
    "nodejs/package.json",
    "common/hogvm/typescript/package.json",
    "common/hogql_parser/package.json",
    "common/plugin_transpiler/package.json",
    "packages/agent/packages/git/package.json",
    "packages/quill/packages/quill/package.json",
    "products/desktop/apps/web/package.json",
    "products/desktop/package.json",
    "products/desktop/packages/shared/package.json",
    "products/desktop/tooling/typescript/package.json",
    "rust/batch-import-worker/scripts/package.json",
    "services/agent-proxy/package.json",
    "services/credentials-service/package.json",
    "services/mcp/package.json",
    "services/stripe-app/package.json",
    "products/desktop/apps/code/package.json",
    "products/desktop/packages/api-client/package.json",
    "packages/agent/packages/agent/package.json",
)


class FlindIdentityContractWave143(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "pyproject.toml").open("rb") as f:
            cls.project = tomllib.load(f)
        with (ROOT / "uv.lock").open("rb") as f:
            cls.lock = tomllib.load(f)

    def test_root_distribution_is_flind(self):
        self.assertEqual(self.project["project"]["name"], "flind")
        root_packages = [p for p in self.lock["package"] if p.get("source") == {"virtual": "."}]
        self.assertEqual(len(root_packages), 1)
        self.assertEqual(root_packages[0]["name"], "flind")
        self.assertIn("flind", self.lock["manifest"]["members"])
        self.assertNotIn(LEGACY, self.lock["manifest"]["members"])

    def test_all_18_curated_private_packages_have_flind_names(self):
        self.assertEqual(len(PRIVATE_FIRST_PARTY), 18)
        for path in PRIVATE_FIRST_PARTY:
            with self.subTest(path=path):
                data = json.loads((ROOT / path).read_text())
                self.assertTrue(data.get("private"))
                self.assertTrue(data["name"].startswith("@flind/"))

    def test_curated_package_metadata_has_no_upstream_brand(self):
        for path in PRIVATE_FIRST_PARTY:
            with self.subTest(path=path):
                data = json.loads((ROOT / path).read_text())
                display = {key: data[key] for key in ("description", "author", "repository", "homepage")
                           if key in data}
                self.assertNotIn(LEGACY, json.dumps(display, ensure_ascii=False).lower())

    def test_first_party_contract_is_explicit_not_a_false_release_pass(self):
        contract = (ROOT / "docs/flind/IDENTITY_CONTRACT.md").read_text()
        self.assertIn("Only Flind", contract)
        self.assertIn("brand_audit.py --strict", contract)
        self.assertIn("expected FAIL", contract)
        self.assertIn("issue #5", contract)
        self.assertIn("issue #82", contract)

    def test_license_attribution_not_destroyed(self):
        for path in ("LICENSE", "products/desktop/LICENSE"):
            with self.subTest(path=path):
                notice = (ROOT / path).read_text()
                self.assertIn("Copyright", notice)


if __name__ == "__main__":
    unittest.main()
