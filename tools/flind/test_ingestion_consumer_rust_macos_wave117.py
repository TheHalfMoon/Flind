"""Wave117 — native Rust ingestion-consumer binary and safe macOS build admission."""
from __future__ import annotations

from pathlib import Path
import os
import platform
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "tools/flind/check_ingestion_consumer_rust_macos_wave117.sh"
DEFAULT_BINARY = Path(
    os.environ.get("FLIND_INGESTION_CONSUMER_BINARY")
    or "/tmp/flind-wave110-rust-target/debug/ingestion-consumer"
)
FULL_RUST = Path(os.environ.get("FLIND_RUST_ROOT") or "/tmp/flind-wave76-frontend/rust")


def source(relative):
    result = subprocess.run(
        ["git", "-c", "maintenance.auto=false", "show", "HEAD:" + relative],
        cwd=ROOT, capture_output=True, text=True, timeout=14, check=False,
    )
    if result.returncode:
        raise AssertionError(f"Source missing in current main: {relative}")
    return result.stdout


class NativeRustIngestionConsumerWave117(unittest.TestCase):
    def test_actual_executable_macho_arm64_binary(self):
        if platform.system() != "Darwin":
            self.skipTest("Native Apple Silicon qualification only")
        self.assertTrue(DEFAULT_BINARY.is_file(), "Native Rust ingestion-consumer binary missing")
        report = subprocess.run(
            ["file", str(DEFAULT_BINARY)], capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(report.returncode, 0)
        self.assertIn("Mach-O 64-bit executable arm64", report.stdout)
        self.assertGreater(DEFAULT_BINARY.stat().st_size, 20 * 1024 * 1024)

    def test_native_source_exactly_matches_main_revision(self):
        if not FULL_RUST.is_dir():
            self.skipTest("Full Rust source checkout not available")
        def rev(repo):
            response = subprocess.run(
                ["git", "rev-parse", "HEAD:rust/ingestion-consumer"],
                cwd=repo, capture_output=True, text=True, timeout=8,
            )
            self.assertEqual(response.returncode, 0)
            return response.stdout.strip()
        self.assertEqual(rev(ROOT), rev(FULL_RUST.parent))

    def test_proto_required_from_source_not_invented(self):
        required = FULL_RUST.parent / "proto/ingestion/worker/v1/worker.proto"
        if not FULL_RUST.is_dir():
            self.skipTest("Full Rust source checkout unavailable")
        self.assertTrue(required.is_file())
        blob = subprocess.run(
            ["git", "hash-object", str(required)],
            cwd=FULL_RUST.parent, capture_output=True, text=True, timeout=8,
        )
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD:proto/ingestion/worker/v1/worker.proto"],
            cwd=FULL_RUST.parent, capture_output=True, text=True, timeout=8,
        )
        self.assertEqual(blob.returncode, 0)
        self.assertEqual(tree.returncode, 0)
        self.assertEqual(blob.stdout.strip(), tree.stdout.strip())

    def test_rust_and_node_topic_and_consumer_group_default_contract(self):
        rust = source("rust/ingestion-consumer/src/config.rs")
        node = source("nodejs/src/ingestion/config.ts")
        kafka = source("nodejs/src/common/config/kafka-topics.ts")
        self.assertRegex(
            rust,
            r'\#\[envconfig\(default\s*=\s*"events_plugin_ingestion"\)\]\s*pub ingestion_consumer_consume_topic',
        )
        self.assertRegex(
            rust,
            r'\#\[envconfig\(default\s*=\s*"events-ingestion-consumer"\)\]\s*pub ingestion_consumer_group_id',
        )
        self.assertIn("INGESTION_CONSUMER_CONSUME_TOPIC: KAFKA_EVENTS_PLUGIN_INGESTION", node)
        self.assertIn("INGESTION_CONSUMER_GROUP_ID: 'events-ingestion-consumer'", node)
        self.assertIn("events_plugin_ingestion", kafka)

    def test_wrapper_offline_and_both_real_cargo_targets(self):
        script = WRAPPER.read_text()
        self.assertIn("cargo check --locked --offline -p ingestion-consumer --lib --bin ingestion-consumer", script)
        self.assertIn("cargo build --locked --offline -p ingestion-consumer --bin ingestion-consumer", script)
        self.assertIn("CARGO_NET_OFFLINE=true", script)
        self.assertIn("FLIND_INGESTION_CONSUMER_BUILD", script)
        self.assertIn("CPLUS_INCLUDE_PATH=", script)
        self.assertIn("SDKROOT=", script)
        self.assertIn("10 * 1024 * 1024", script)
        self.assertIn("proto/ingestion/worker/v1/worker.proto", script)

    def test_wrapper_refuses_fake_workspace_without_proto(self):
        if platform.system() != "Darwin" or platform.machine() not in ("arm64", "aarch64"):
            self.skipTest("Native Apple Silicon only")
        with tempfile.TemporaryDirectory(prefix="flind-wave117-no-proto-") as folder:
            fake_rust = Path(folder) / "rust"
            fake_rust.mkdir()
            (fake_rust / "Cargo.toml").write_text("[workspace]\n")
            (fake_rust / "Cargo.lock").write_text("# Fake fixture only\n")
            result = subprocess.run(
                ["bash", str(WRAPPER)],
                env={**os.environ, "FLIND_RUST_ROOT": str(fake_rust)},
                capture_output=True, text=True, timeout=13,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing first-party ingestion-worker protobuf", result.stderr)

    def test_script_is_syntactically_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(WRAPPER)], capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
