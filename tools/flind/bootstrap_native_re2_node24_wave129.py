#!/usr/bin/env python3
"""Build or verify pinned native RE2 locally under Node24 (never global Node).

Works only in Flind's preexisting scratch pnpm lockfile dependency tree.
Uses Node24's installed headers and macOS SDK; no downloads, no paid cloud.
Bounds CPU jobs, elapsed time, and free disk. Does not edit Git files.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

SCRATCH = Path("/tmp/flind-wave76-frontend")
RE2 = SCRATCH / "node_modules/.pnpm/re2@1.22.1_supports-color@10.2.2/node_modules/re2"
BINDING = RE2 / "build/Release/re2.node"
NODE24 = Path("/opt/homebrew/Cellar/node@24/24.15.0")
GYP = Path("/opt/homebrew/lib/node_modules/npm/node_modules/@npmcli/run-script/lib/node-gyp-bin/node-gyp")
MIN_FREE = 10_500_000_000
LOG = Path("/tmp/flind-wave129-native-re2-safe-build.log")


def verify_import() -> bool:
    if not BINDING.is_file():
        return False
    env = dict(os.environ)
    env["PATH"] = str(NODE24 / "bin") + ":" + env.get("PATH", "/usr/bin:/bin")
    try:
        result = subprocess.run(
            [str(NODE24 / "bin/node"), "-e", "const RE2=require('re2');if(!new RE2('a+').test('aaa'))process.exit(2)"],
            cwd=SCRATCH / "nodejs", env=env,
            capture_output=True, timeout=8,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def qualify() -> dict:
    report = {
        "node24_local_native_re2_qualified": False,
        "pinned_native_dependency": "re2@1.22.1",
        "node24_global_switch": False,
        "paid_cloud_used": False,
        "release_qualified": False,
    }
    for candidate in (RE2 / "binding.gyp", NODE24 / "bin/node", NODE24 / "include/node/node.h", GYP):
        if not candidate.is_file():
            return {**report, "blocker": "Pinned local RE2/Node24 build source unavailable"}
    if verify_import():
        return {**report, "node24_local_native_re2_qualified": True, "existing_native_binding_reused": True}
    if shutil.disk_usage("/tmp").free < MIN_FREE + 1024**3:
        return {**report, "blocker": "Insufficient disk reserve for native build"}
    try:
        sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True,
                             text=True, check=True, timeout=8).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {**report, "blocker": "macOS SDK not available"}
    if not (Path(sdk) / "usr/include/c++/v1/string").is_file():
        return {**report, "blocker": "macOS libc++ headers missing"}
    env = dict(os.environ)
    env.update({
        "PATH": str(NODE24 / "bin") + ":" + env.get("PATH", "/usr/bin:/bin"),
        "SDKROOT": sdk,
        "npm_config_jobs": "2",
        "CPLUS_INCLUDE_PATH": sdk + "/usr/include/c++/v1:/opt/homebrew/include:" + str(NODE24 / "include/node"),
        "C_INCLUDE_PATH": "/opt/homebrew/include:" + str(NODE24 / "include/node"),
        "CXXFLAGS": "-O0 -isysroot " + sdk + " -I" + sdk +
                    "/usr/include/c++/v1 -I/opt/homebrew/include -I" + str(NODE24 / "include/node"),
    })
    cmd = [str(GYP), "-j", "2", "rebuild", "--nodedir=" + str(NODE24)]
    try:
        with LOG.open("wb") as output:
            child = subprocess.Popen(cmd, cwd=RE2, env=env, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            began = time.monotonic()
            stop = None
            while child.poll() is None:
                if shutil.disk_usage("/tmp").free < MIN_FREE:
                    stop = "10.5GB disk reserve"
                    break
                if time.monotonic() - began > 100:
                    stop = "100-second native build bound"
                    break
                time.sleep(2)
            if stop and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=7)
        if child.returncode != 0 or stop:
            return {**report, "blocker": stop or "Pinned native RE2 compile failed",
                    "native_build_exit": child.returncode}
    except (OSError, subprocess.SubprocessError):
        return {**report, "blocker": "Failed to launch pinned native build"}
    return {**report, "node24_local_native_re2_qualified": verify_import(),
            "existing_native_binding_reused": False}


if __name__ == "__main__":
    receipt = qualify()
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["node24_local_native_re2_qualified"] else 2)
