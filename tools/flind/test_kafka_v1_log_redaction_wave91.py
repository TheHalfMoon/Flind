"""Guard Kafka v1 lifecycle logs against native config credential disclosure."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.ts"
SAFE = ROOT / "nodejs/src/common/kafka/consumer/safe-log-context.ts"
JEST = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.test.ts"


class KafkaV1CredentialsLogWave91(unittest.TestCase):
    def test_diagnostic_context_is_allowlisted_in_all_four_lifecycle_paths(self):
        source = V1.read_text(encoding="utf-8")
        self.assertEqual(source.count("safeKafkaLogContext(this.config)"), 4)
        self.assertIn("'librdkafka consumer subscribed'", source)
        self.assertIn("'librdkafka connection failure'", source)
        self.assertIn("'consumer_loop_error'", source)
        self.assertIn("'failed to stop consumer loop safely. Continuing shutdown'", source)
        self.assertNotIn("config: this.consumerConfig", source)
        self.assertNotIn("consumerConfig: this.consumerConfig", source)

    def test_native_connection_failure_does_not_log_raw_error_or_metrics_objects(self):
        source = V1.read_text(encoding="utf-8")
        begin = source.index("consumer.on('connection.failure'")
        end = source.index("consumer.on('offset.commit'", begin)
        block = source[begin:end]
        # Wave94 now validates the numeric code in the shared native error allowlist.
        self.assertIn("...safeKafkaErrorContext(error)", block)
        self.assertIn("...safeKafkaLogContext(this.config)", block)
        self.assertNotIn("metrics,", block)
        self.assertNotIn("error,", block)

    def test_safe_context_is_constructed_from_explicit_fields_only(self):
        source = SAFE.read_text(encoding="utf-8")
        self.assertRegex(source, r"return\s*\{\s*topic:\s*config.topic,\s*groupId:\s*config.groupId\s*\}")
        self.assertNotIn("...config", source)
        self.assertNotIn("JSON.stringify(config)", source)

    def test_real_jest_regressions_cover_sensitive_native_client_callbacks(self):
        source = JEST.read_text(encoding="utf-8")
        self.assertIn("secret-safe Kafka lifecycle diagnostics (Wave 91)", source)
        self.assertIn("synthetic-private-kafka-sasl-token", source)
        self.assertIn("synthetic-secret-in-native-metrics", source)
        self.assertIn("not.toContain(secret)", source)


if __name__ == "__main__":
    unittest.main()
