"""Wave124 checks that the real gRPC WorkerIngest server uses the safe converter.

These are source integration guards; the native Node suite executes the actual
pure TypeScript converter and is the behavioral proof.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "nodejs/src/ingestion/api"


class GrpcSafeInt64SourceWave124(unittest.TestCase):
    def test_server_uses_safe_converter_for_every_incoming_message(self):
        server = (API / "grpc-server.ts").read_text()
        self.assertIn("import { grpcMessageToSerialized } from './grpc-message-converter'", server)
        self.assertIn("export { grpcMessageToSerialized } from './grpc-message-converter'", server)
        self.assertIn("subBatch.messages.map(grpcMessageToSerialized)", server)
        self.assertNotIn("offset: Number(message.offset)", server)
        self.assertNotIn("timestamp: Number(message.timestamp)", server)

    def test_converter_has_no_runtime_package_dependencies(self):
        text = (API / "grpc-message-converter.ts").read_text()
        self.assertIn("import type { KafkaMessage }", text)
        self.assertIn("import type { SerializedKafkaMessage }", text)
        self.assertNotIn("import { KafkaMessage }", text)
        self.assertIn("export function grpcMessageToSerialized", text)

    def test_int64_admission_prevents_precision_loss(self):
        text = (API / "grpc-message-converter.ts").read_text()
        self.assertIn("Number.isSafeInteger(asNumber)", text)
        self.assertIn("BigInt(asNumber) !== value", text)
        self.assertIn("throw new RangeError", text)
        self.assertIn("checkedInt64(message.offset, 'offset')", text)
        self.assertIn("checkedInt64(message.timestamp, 'timestamp')", text)

    def test_original_rust_grpc_wire_defines_int64_fields(self):
        import subprocess
        result = subprocess.run(
            ["git", "show", "HEAD:proto/ingestion/worker/v1/worker.proto"],
            cwd=ROOT, capture_output=True, text=True, timeout=12, check=True,
        )
        self.assertIn("int64 offset = 3;", result.stdout)
        self.assertIn("int64 timestamp = 4;", result.stdout)
        self.assertIn("optional string key = 5;", result.stdout)

    def test_node_regressions_and_original_jest_suite_present(self):
        native = (ROOT / "tools/flind/test_node_grpc_int64_wave124.mjs").read_text()
        jest = (API / "grpc-message-converter.test.ts").read_text()
        for name in (
            "unsafe positive offset immediately fails closed",
            "unsafe negative offset fails closed",
            "unsafe timestamp fails closed",
            "Kafka null tombstone value and key remain null",
        ):
            self.assertIn(name, native)
        self.assertIn("refuses a rounded Kafka offset", jest)
        self.assertIn("refuses an unsafe Protobuf timestamp", jest)


if __name__ == "__main__":
    unittest.main()
