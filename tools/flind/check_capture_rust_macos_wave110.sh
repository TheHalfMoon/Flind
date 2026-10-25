#!/usr/bin/env bash
# Flind: a source-local, offline Apple Silicon Capture Rust build admission check.
# Sets SDK paths only for the child process: never changes global host settings.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "This qualification is for native Apple Silicon macOS only." >&2
    exit 2
fi
if ! command -v xcrun >/dev/null || ! command -v cargo >/dev/null; then
    echo "Apple developer tools and Cargo are required." >&2
    exit 2
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
rust_root="${FLIND_RUST_ROOT:-$project_root/rust}"
if [[ ! -f "$rust_root/Cargo.toml" || ! -f "$rust_root/Cargo.lock" ]]; then
    echo "Rust workspace is not fully available; supply FLIND_RUST_ROOT." >&2
    exit 2
fi

sdk_root="$(xcrun --show-sdk-path)"
if [[ ! -f "$sdk_root/usr/include/c++/v1/iostream" ]]; then
    echo "macOS SDK libc++ headers are unavailable." >&2
    exit 2
fi

# Stock Apple clang may not automatically locate C++ libc++ SDK headers
# when librdkafka is built by rdkafka-sys's Makefiles. Keep existing overrides
# and avoid writing to ~/.cargo, shell profile, or system developer settings.
export SDKROOT="$sdk_root"
export CPLUS_INCLUDE_PATH="$sdk_root/usr/include/c++/v1${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
export CARGO_NET_OFFLINE=true
export CARGO_INCREMENTAL=0
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"

cd "$rust_root"
exec cargo check --locked --offline -p capture --lib --bin capture --jobs "$CARGO_BUILD_JOBS"
