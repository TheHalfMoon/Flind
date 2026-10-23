#!/usr/bin/env python3
"""Lightweight zero-dependency assertions for initial Flind identity surfaces."""
from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
manifest = json.loads((root / "frontend/public/site.webmanifest").read_text())
head = (root / "posthog/templates/head.html").read_text()
reauth = (root / "posthog/templates/sso_reauth_complete.html").read_text()
readme = (root / "README.md").read_text()

checks = {
    "manifest name": manifest.get("name") == "Flind" and manifest.get("short_name") == "Flind",
    "HTML default title": 'page_title|default:"Flind"' in head,
    "HTML app name": 'content="Flind"' in head,
    "HTML OG site": 'property="og:site_name" content="Flind"' in head,
    "SSO page title": "<title>Flind</title>" in reauth,
    "Flind README": readme.startswith("# Flind\n"),
    "root license kept": (root / "LICENSE").is_file(),
    "enterprise license kept": (root / "ee/LICENSE").is_file(),
}
for name, good in checks.items():
    print(f'{"PASS" if good else "FAIL"}: {name}')
if not all(checks.values()):
    raise SystemExit(1)
print("PASS: Flind foundation brand checks complete (NOT a full product test)")
