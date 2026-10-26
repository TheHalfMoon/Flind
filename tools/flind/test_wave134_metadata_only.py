#!/usr/bin/env python3
"""Wave 134: strictly metadata-only branding of existing private Flind workspaces."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(os.environ.get("FLIND_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
REF = "HEAD"
BASE = "0c4b6688f8b108304a2bff5e8245c4c95172439b"
SAFE_METADATA = frozenset(("description", "author", "repository"))
PACKAGES = (
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
)


def tracked(path: str, ref: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{ref}:{path}"], text=True, timeout=30
    )


class Wave134(unittest.TestCase):
    def test_every_change_is_metadata_only(self):
        self.assertEqual(len(PACKAGES), 11)
        for path in PACKAGES:
            with self.subTest(package=path):
                previous = json.loads(tracked(path, BASE))
                actual = json.loads(tracked(path, REF))
                self.assertTrue(actual.get("private"))
                self.assertTrue(actual["name"].startswith("@flind/"))
                changed = {key for key in set(previous) | set(actual)
                           if previous.get(key) != actual.get(key)}
                self.assertTrue(changed, f"No change for {path}")
                self.assertTrue(changed <= SAFE_METADATA, f"{path}: {sorted(changed)}")
                for key in ("name", "version", "license", "private", "scripts",
                            "dependencies", "devDependencies", "peerDependencies",
                            "optionalDependencies", "exports"):
                    self.assertEqual(previous.get(key), actual.get(key), (path, key))

    def test_display_metadata_contains_no_inherited_vendor(self):
        for path in PACKAGES:
            with self.subTest(package=path):
                data = json.loads(tracked(path, REF))
                for key in SAFE_METADATA:
                    value = data.get(key)
                    if value is not None:
                        self.assertNotIn("posthog", json.dumps(value).lower(), (path, key))

    def test_original_copyright_and_notices_unchanged(self):
        for path in ("LICENSE", "packages/quill/LICENSE", "products/desktop/LICENSE"):
            with self.subTest(notice=path):
                self.assertEqual(tracked(path, BASE), tracked(path, REF))
        self.assertIn("Copyright (c)", tracked("LICENSE", REF))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="HEAD")
    args, remaining = parser.parse_known_args()
    REF = args.ref
    unittest.main(argv=[__file__, *remaining])
