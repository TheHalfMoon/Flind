"""Enumerate tracked legacy-identity residue across the Flind source tree.

Read-only. Uses Git's tracked-file list, avoiding machine caches and .git blobs.
Zero is the *future* release gate; failures are expected during migration.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
LEGACY = "post" + "hog"


def run(*args: str) -> bytes:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.decode("utf-8", "replace"))
    return proc.stdout


def audit() -> dict[str, object]:
    paths = [
        part.decode("utf-8", "replace")
        for part in run("ls-files", "-z").split(b"\0") if part
    ]
    bad_names = [name for name in paths if LEGACY in name.casefold()]
    bad_contents = [
        part.decode("utf-8", "replace")
        for part in run("grep", "-Iilz", LEGACY, "--").split(b"\0") if part
    ]
    by_area = Counter(name.split("/", 1)[0] for name in bad_contents)
    return {
        "scope": "tracked paths and searchable text blobs, not Git history, binaries or generated builds",
        "tracked_files": len(paths),
        "paths_with_legacy_identity": len(bad_names),
        "text_files_with_legacy_identity": len(bad_contents),
        "identity_gate_passed": not bad_names and not bad_contents,
        "top_areas": dict(sorted(by_area.items(), key=lambda item: (-item[1], item[0]))[:15]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit 2 until zero brand residue")
    args = parser.parse_args()
    summary = audit()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 2 if args.strict and not summary["identity_gate_passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
