#!/usr/bin/env bash
# Qualify first-party Rust ingestion-consumer on native Apple Silicon.
# Offline/no cloud; no global SDK changes; no user data or shared services.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "Flind native Rust ingestion-consumer qualification requires Apple Silicon macOS." >&2
    exit 2
fi
for tool in xcrun cargo; do
    command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 2; }
done
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
rust_root="${FLIND_RUST_ROOT:-$root/rust}"
if [[ ! -f "$rust_root/Cargo.lock" || ! -f "$rust_root/Cargo.toml" ]]; then
    echo "A complete Rust workspace is required; set FLIND_RUST_ROOT." >&2
    exit 2
fi
if [[ ! -f "$rust_root/../proto/ingestion/worker/v1/worker.proto" ]]; then
    echo "Missing first-party ingestion-worker protobuf source: check out proto/." >&2
    exit 2
fi
sdk_root="$(xcrun --show-sdk-path)"
[[ -f "$sdk_root/usr/include/c++/v1/iostream" ]] || {
    echo "macOS SDK C++ headers are missing." >&2
    exit 2
}
# Retain a 10-GiB free-disk floor before compilation. Long executions should
# also be monitored externally to bound scratch-disk consumption.
free_kib="$(df -Pk /tmp | awk 'NR==2 {print $4}')"
if (( free_kib < 10 * 1024 * 1024 )); then
    echo "Less than 10GiB free disk; refusing Rust build." >&2
    exit 2
fi

export SDKROOT="$sdk_root"
export CPLUS_INCLUDE_PATH="$sdk_root/usr/include/c++/v1${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
export CARGO_NET_OFFLINE=true
export CARGO_INCREMENTAL=0
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"

cd "$rust_root"
if [[ "${FLIND_INGESTION_CONSUMER_BUILD:-0}" == "1" ]]; then
    exec cargo build --locked --offline -p ingestion-consumer --bin ingestion-consumer --jobs "$CARGO_BUILD_JOBS"
fi
exec cargo check --locked --offline -p ingestion-consumer --lib --bin ingestion-consumer --jobs "$CARGO_BUILD_JOBS"
