"""Wave 94: native Kafka error logs cannot serialize credential-bearing objects."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.ts"
HELPER = ROOT / "nodejs/src/common/kafka/consumer/safe-log-context.ts"
TESTS = ROOT / "nodejs/src/common/kafka/consumer/safe-log-context.test.ts"


class KafkaNativeDiagnosticPrivacyWave94(unittest.TestCase):
    def test_unsafe_error_text_never_enters_consumer_diagnostics(self):
        source = SRC.read_text(encoding="utf-8")
        forbidden = [
            "error: String(error)", "error: String(e)", "error: error",
            "error: error.message", "errorStack:", "error.stack",
            "error.message", "logger.error('🔥', 'kafka_consumer_rebalancing_error', { err })",
            "'librdkafka log', { log: log }", "message: error.message",
            "logger.warn('📝', 'librdkafka_offet_commit_error', { error,",
            "captureException(err)", "captureException(e)",
            "captureException(error)",
        ]
        for leak in forbidden:
            with self.subTest(leak=leak):
                self.assertNotIn(leak, source)

    def test_all_native_callbacks_have_allowlisted_diagnostics(self):
        source = SRC.read_text(encoding="utf-8")
        for event in (
            "librdkafka_error", "librdkafka connection failure",
            "librdkafka_offet_commit_error", "connect_error", "main_loop_error",
            "consumer_loop_error", "offset_gate_drain_failed_during_revocation",
            "partition_revocation_failed", "partition_revoked_handler_failed",
        ):
            with self.subTest(event=event):
                start = source.index("'" + event + "'")
                self.assertIn("safeKafkaErrorContext(", source[start:start + 210])
        self.assertIn("logger.info('📝', 'librdkafka_log_event')", source)
        self.assertIn("details.assignmentError = 'Kafka partition assignment unavailable'", source)
        self.assertIn("Object.assign(details, safeKafkaErrorContext(error))", source)

    def test_allowlist_rejects_secret_strings_and_unbounded_numbers(self):
        helper = HELPER.read_text(encoding="utf-8")
        self.assertIn("export function safeKafkaErrorContext(error: unknown)", helper)
        self.assertIn("Number.isSafeInteger(code)", helper)
        self.assertIn("Number.isSafeInteger(errno)", helper)
        self.assertIn("typeof isFatal === 'boolean'", helper)
        self.assertIn("typeof isRetriable === 'boolean'", helper)
        self.assertNotIn("String(error)", helper)
        self.assertNotIn("JSON.stringify(error)", helper)

    def test_actual_jest_regressions_cover_unsafe_error_objects(self):
        tests = TESTS.read_text(encoding="utf-8")
        for marker in (
            "Kafka native diagnostic error privacy (Wave 94)",
            "keeps numeric codes and boolean flags",
            "does not invoke String(error)",
            "tolerates malicious error-field getters",
            "excludes NaN, infinity",
        ):
            self.assertIn(marker, tests)


if __name__ == "__main__":
    unittest.main()
