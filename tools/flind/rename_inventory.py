"""Count what is still named PostHog in this repository, and hold the line while the full rename lands.

The owner decided (2026-11-10) that everything becomes Flind: paths, the Python package, JS packages, UI text,
configuration, database tables and vendored SDKs. Only the LICENSE copyright notices stay.

    python tools/flind/rename_inventory.py            # print counts
    python tools/flind/rename_inventory.py --write    # store them as the new baseline
    python tools/flind/rename_inventory.py --check    # fail if any count is above the baseline

Each rename PR lowers the counts and runs --write; --check stops new PostHog references from coming back.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "flind" / "rename" / "baseline.json"
# Legally required notices and this tooling's own description of what it counts.
EXEMPT = {
    "LICENSE",
    "ee/LICENSE",
    "flind/rename/baseline.json",
    "flind/rename/PLAN.md",
    "flind/STATUS.md",
    "tools/flind/rename_inventory.py",
    "tools/flind/rename_text.py",
    "tools/flind/rename_text_ts.cjs",
    ".github/workflows/flind-rename-ratchet.yml",
}


def category(path: str) -> str:
    if path.endswith((".md", ".mdx")):
        return "docs"
    if path.endswith(".py"):
        return "python"
    if path.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")):
        return "js_ts"
    if path.endswith(".rs") or path.endswith(("Cargo.toml", "Cargo.lock")):
        return "rust"
    if path.endswith((".go", "go.mod", "go.sum")):
        return "go"
    if path.endswith((".html", ".txt", ".ambr", ".snap", ".jinja", ".j2")):
        return "templates_snapshots"
    if path.endswith((".yml", ".yaml", ".toml", ".json", ".json5", ".ini", ".cfg", ".env", ".lock")) or "Dockerfile" in path:
        return "config"
    return "other"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def inventory() -> dict[str, int]:
    counts: Counter[str] = Counter()
    counts["paths"] = sum(1 for f in git("ls-files").splitlines() if re.search("posthog", f, re.I) and f not in EXEMPT)
    for line in git("grep", "-I", "-c", "-i", "posthog").splitlines():
        path, n = line.rsplit(":", 1)
        if path in EXEMPT:
            continue
        counts[f"occurrences_{category(path)}"] += int(n)
    for line in git("grep", "-I", "-c", "PostHog").splitlines():
        path, n = line.rsplit(":", 1)
        if path not in EXEMPT:
            counts["capitalised_PostHog"] += int(n)
    return dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = inventory()
    print(json.dumps(current, indent=2))
    if args.write:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    if args.check:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        grown = {k: (baseline.get(k, 0), v) for k, v in current.items() if v > baseline.get(k, 0)}
        if grown:
            for key, (before, now) in grown.items():
                print(f"MORE POSTHOG: {key} went from {before} to {now}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
