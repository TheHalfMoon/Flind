# Wave 111 — Real native Rust Capture HTTP startup on isolated Redis

## Result: Native executable startup and HTTP router PASS

Using the real **85 MB Mach-O arm64** `capture` executable compiled by Wave110, `tools/flind/qualify_native_capture_server_wave111.py` starts an **actual** temporary Redis server and the production Rust HTTP service using only new loopback ports and sanitized synthetic configuration. It does **not** use the older Python synthetic HTTP Capture receiver as a substitute.

The harness:
- refuses to run without a locally available native Capture binary, Redis server or at least **10 GiB** free disk;
- takes the Capture binary from `FLIND_CAPTURE_BINARY` (default `rust/target/debug/capture`) and Redis from `FLIND_REDIS_BINARY`, `PATH` or the known free temporary Redis toolchain fallback;
- spawns Redis bound only to `127.0.0.1`, without AOF or RDB persistence, with 32 MiB max memory;
- launches the production Capture executable with a **fresh minimal environment**: `ADDRESS=127.0.0.1:<random>`, `REDIS_URL=redis://127.0.0.1:<random>/`, `NOOP_SINK=true`, `PRINT_SINK=false`, Prometheus and rate limits disabled, and deliberately unreachable `KAFKA_HOSTS=127.0.0.1:65441`. No inherited application tokens, API keys, databases, cloud endpoints or production configuration are passed to the child;
- proves the actual `/_liveness` request returns **HTTP 200** and a request missing required authorization to the native `/i/v1/analytics/events` endpoint returns **HTTP 401**;
- forcibly stops both owned processes and deletes their temporary on-disk state/logs, including on errors.

## Actual macOS result — October 26, 2026

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 tools/flind/qualify_native_capture_server_wave111.py
```

**Exit 0**. Native binary present, temporary Redis started, real Capture HTTP bound, real liveness HTTP 200, unauthorized Capture POST HTTP 401; no-sink enabled, loopback-only, both owned child processes stopped. Mac retained ~15 GiB free.

```sh
FLIND_CAPTURE_BINARY=/tmp/flind-wave110-rust-target/debug/capture \
python3 -m unittest -v tools.flind.test_native_capture_server_wave111
```

**5/5 tests PASS**, including an actual second native startup/test/cleanup and fail-closed missing executable / Redis and subprocess termination guards. Does not require Docker, paid cloud services or fixture changes to Rust code.

## Absolute boundary

**The native Capture server is demonstrably running and serving HTTP, but has NOT accepted an authorized event in this harness.** It uses a NOOP output sink, so it does not establish Kafka delivery. Real Rust Capture→Kafka producer/consumer→ClickHouse persisted product events→authenticated query API→Dashboard, multi-tenant access permissions, OAuth/browser/frontend and release remain **false/unqualified** under issue #82. This is a native server smoke, not a deployment or a production-ready claim.

The code in `rust/capture` came from the same Rust tree as current main, qualified in Wave110. Repository stays private, inherited Actions disabled, donor legal attribution unchanged, no publication or paid tools.
