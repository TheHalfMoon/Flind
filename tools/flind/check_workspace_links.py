#!/usr/bin/env python3
"""Inspect the first-party pnpm workspace graph before package renaming.

Dependency-free: runs without installing JS packages or connecting to npm.
This is a *source-consistency* gate, not a build, e2e, or release pass.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
_DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
_NON_ROOT_WORKSPACE_PATHS = (".github/", ".depot/")
_OLD_NAMESPACE = "@post" + "hog/"


def inspect_packages(packages: Iterable[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    manifests = list(packages)
    names: dict[str, list[str]] = defaultdict(list)
    for path, manifest in manifests:
        package_name = manifest.get("name")
        if isinstance(package_name, str) and package_name:
            names[package_name].append(path)

    duplicate_names = {
        name: paths
        for name, paths in sorted(names.items())
        if len([path for path in paths if not path.startswith(_NON_ROOT_WORKSPACE_PATHS)]) > 1
    }

    broken_edges = []
    edges = 0
    for path, manifest in manifests:
        for field in _DEPENDENCY_FIELDS:
            dependencies = manifest.get(field) or {}
            if not isinstance(dependencies, dict):
                broken_edges.append({"file": path, "reason": f"{field} is not a mapping"})
                continue
            for dependency, spec in dependencies.items():
                if not isinstance(spec, str) or not spec.startswith("workspace:"):
                    continue
                edges += 1
                if dependency not in names:
                    broken_edges.append(
                        {"file": path, "dependency": dependency, "specifier": spec, "reason": "unresolved workspace package"}
                    )

    unprotected_flind_packages = [
        {"file": path, "name": name}
        for path, manifest in manifests
        if (name := manifest.get("name")) and isinstance(name, str)
        and name.startswith("@flind/") and manifest.get("private") is not True
    ]
    legacy_packages = sorted(
        name for name in names if name.startswith(_OLD_NAMESPACE)
    )
    return {
        "manifests": len(manifests),
        "named_packages": len(names),
        "workspace_dependency_edges": edges,
        "flind_package_names": sorted(name for name in names if name.startswith("@flind/")),
        "remaining_legacy_package_names": legacy_packages,
        "duplicate_active_package_names": duplicate_names,
        "unresolved_workspace_dependencies": broken_edges,
        "unprotected_flind_packages": unprotected_flind_packages,
        "workspace_gate_passed": not (duplicate_names or broken_edges or unprotected_flind_packages),
        "package_identity_gate_passed": not legacy_packages,
    }


def load_tracked_package_manifests(root: Path) -> list[tuple[str, dict[str, Any]]]:
    raw_paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "*package.json"], cwd=root
    )
    manifests = []
    for raw_name in raw_paths.decode("utf-8").split("\0"):
        if not raw_name:
            continue
        file = root / raw_name
        if not file.is_file():
            raise FileNotFoundError(f"Missing tracked package manifest: {raw_name}")
        manifest = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise TypeError(f"Invalid package manifest: {raw_name}")
        manifests.append((raw_name, manifest))
    return manifests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-no-legacy", action="store_true", help="Require all tracked npm workspace package names to use their migrated first-party scope (not a full source identity audit)")
    args = parser.parse_args()
    result = inspect_packages(load_tracked_package_manifests(REPO_ROOT))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["workspace_gate_passed"]:
        return 1
    if args.require_no_legacy and not result["package_identity_gate_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
