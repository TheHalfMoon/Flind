#!/usr/bin/env python3
"""Deterministic, local-only QA for both Flind Desktop-derived mobile clients.

Never installs dependencies, deploys, publishes, enables GitHub Actions, or
uses external services. Build prerequisites in dependency order, then run
the original Vitest suites and TypeScript gates. Use --skip-build for reruns.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / "packages/agent"
DESKTOP = ROOT / "products/desktop"
NODE24 = Path("/opt/homebrew/opt/node@24/bin")
VITEST = DESKTOP / "node_modules/.bin/vitest"


def run_step(label: str, cwd: Path, command: list[str], env: dict[str, str]) -> bool:
    print(f"\n[{label}] {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    print(f"[{label}] {'PASS' if completed.returncode == 0 else 'FAIL'} "
          f"(exit {completed.returncode})", flush=True)
    return completed.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true",
                        help="Reuse already built agent, shared and platform workspaces")
    args = parser.parse_args()
    env = os.environ.copy()
    if NODE24.is_dir():
        env["PATH"] = str(NODE24) + os.pathsep + env.get("PATH", "")
    env.setdefault("NODE_OPTIONS", "--max-old-space-size=2500")

    if not shutil.which("pnpm", path=env.get("PATH")):
        print("FAIL: pnpm unavailable. Install with the checked-in lockfiles first.")
        return 2
    if not VITEST.exists():
        print("FAIL: Vitest unavailable. Install checked-in Desktop dependencies "
              "with frozen lockfile and --ignore-scripts before qualification.")
        return 2
    steps: list[tuple[str, Path, list[str]]] = []
    if not args.skip_build:
        steps.extend([
            ("Agent dependency graph", AGENT,
             ["pnpm", "-r", "--workspace-concurrency=1",
              "--filter", "@flind/agent...", "run", "build"]),
            ("Desktop shared", DESKTOP, ["pnpm", "--filter", "@flind/shared", "build"]),
            ("Desktop platform", DESKTOP, ["pnpm", "--filter", "@flind/platform", "build"]),
        ])
    steps.extend([
        ("Mobile Studio TypeScript", DESKTOP,
         ["pnpm", "--filter", "@flind/mobile-studio", "typecheck"]),
        ("Mobile TypeScript baseline", DESKTOP,
         ["pnpm", "--filter", "@flind/mobile", "typecheck"]),
        ("Mobile Studio Vitest", DESKTOP / "apps/mobilehog",
         [str(VITEST), "run", "--maxWorkers=2"]),
        ("Mobile Vitest", DESKTOP / "apps/mobile",
         [str(VITEST), "run", "--maxWorkers=2"]),
    ])
    for label, cwd, command in steps:
        if not run_step(label, cwd, command, env):
            print(f"\nNO-GO: stopped at {label}; no later gate was marked PASS.")
            return 1
    print("\nPASS: both mobile local TypeScript gates and both original Vitest suites.")
    baseline = json.loads((DESKTOP / "scripts/mobile-type-baseline.json").read_text())
    remaining = sum(
        count for by_error in baseline.get("files", {}).values()
        for count in by_error.values()
    )
    if remaining:
        print(f"NOTE: mobile has {remaining} inherited TypeScript error(s) in its baseline.")
    else:
        print("PASS: Mobile TypeScript baseline is empty; tsc reports zero errors.")
    print("NO-GO release until device, server, OAuth, SDK and storage tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
