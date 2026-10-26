#!/usr/bin/env python3
"""Wave133: evaluate real AEO setting expression and verify first-party npm metadata.

No Django import, npm install, runtime egress or database access.
Execute: python3 tools/flind/test_wave133_aeo_metadata.py --ref <branch>
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(os.environ.get('FLIND_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
REF = "HEAD"
META = (
    "nodejs/package.json",
    "common/hogvm/typescript/package.json",
    "common/hogql_parser/package.json",
    "common/plugin_transpiler/package.json",
)


def tracked_text(path: str, ref: str = REF) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{ref}:{path}"],
        text=True,
        timeout=25,
    )


def aeo_setting(env: dict[str, str], ref: str) -> list[str]:
    tree = ast.parse(tracked_text("posthog/settings/web.py", ref))
    value = next(
        node.value
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(isinstance(t, ast.Name) and t.id == "AEO_TARGET_DOMAINS"
                for t in (node.targets if isinstance(node, ast.Assign) else [node.target]))
    )
    def get_from_env(name: str, default: str) -> str:
        return env.get(name, default)
    def get_list(raw: str) -> list[str]:
        return [s.strip() for s in raw.split(",") if s.strip()]
    compiled = compile(ast.Expression(body=value), "<actual AEO setting>", "eval")
    return eval(compiled, {"get_from_env": get_from_env, "get_list": get_list})


class Wave133(unittest.TestCase):
    def test_aeo_default_never_inherits_donor_domain(self):
        self.assertEqual(aeo_setting({}, REF), [])

    def test_aeo_explicit_operator_domain_supported(self):
        self.assertEqual(
            aeo_setting({"AEO_TARGET_DOMAINS": "flind.example, docs.flind.example"}, REF),
            ["flind.example", "docs.flind.example"],
        )

    def test_aeo_explicit_empty_is_disabled(self):
        self.assertEqual(aeo_setting({"AEO_TARGET_DOMAINS": ""}, REF), [])

    def test_package_identity_and_version_stable(self):
        for path in META:
            with self.subTest(package=path):
                data = json.loads(tracked_text(path, REF))
                self.assertTrue(data["private"])
                self.assertTrue(data["name"].startswith("@flind/"))
                self.assertEqual(data.get("author"), "Flind Contributors")
                self.assertNotIn("posthog", data.get("description", "").lower())
                repository = data.get("repository")
                if isinstance(repository, str):
                    self.assertNotIn("posthog", repository.lower())
                self.assertIn("version", data)
                self.assertIn("license", data)

    def test_required_license_attribution_retained(self):
        # Copyright and mandatory legal notices are not branding copy.
        self.assertIn("Copyright (c)", tracked_text("LICENSE", REF))
        self.assertIn("PostHog", tracked_text("LICENSE", REF))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="HEAD")
    args, unittest_args = parser.parse_known_args()
    REF = args.ref
    unittest.main(argv=[__file__, *unittest_args])
