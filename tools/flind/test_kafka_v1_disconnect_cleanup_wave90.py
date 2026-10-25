"""Wave90 guardrails: Kafka v1 disconnect must not skip native teardown."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.ts"
TESTS = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.test.ts"


class V1DisconnectCleanupWave90(unittest.TestCase):
    def disconnect_source(self) -> str:
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("    public async disconnect(): Promise<void> {")
        end = source.index("    private async disconnectConsumer(): Promise<void> {", start)
        return source[start:end]

    def test_rejected_tasks_are_settled_without_exiting_before_teardown(self):
        method = self.disconnect_source()
        self.assertIn("await Promise.allSettled(this.backgroundTask.map((t) => t.promise))", method)
        self.assertNotIn("await Promise.all(this.backgroundTask.map((t) => t.promise))", method)
        self.assertIn("await this.disconnectConsumer()", method)
        self.assertLess(method.index("await this.offsetCommitGate.drain()"),
                        method.index("await this.disconnectConsumer()"))

    def test_all_failure_paths_preserve_cause_after_native_disconnect(self):
        method = self.disconnect_source()
        self.assertIn("failures.push(error)", method)
        self.assertIn("this.offsetCommitGate.failed", method)
        self.assertIn("new AggregateError(failures, 'Kafka consumer shutdown failed')", method)
        self.assertLess(method.index("await this.disconnectConsumer()"), method.index("throw failures[0]"))
        self.assertLess(method.index("await this.disconnectConsumer()"), method.index("throw new AggregateError"))

    def test_real_mock_kafka_tests_cover_failure_and_success(self):
        tests = TESTS.read_text(encoding="utf-8")
        self.assertIn("describe('failed background work shutdown (Wave 90)'", tests)
        self.assertIn("toBe(backgroundError)", tests)
        self.assertIn("not.toHaveBeenCalled()", tests)
        self.assertIn("expect(observed).toBeInstanceOf(AggregateError)", tests)
        self.assertIn("expect(mockRdKafkaConsumer.disconnect).toHaveBeenCalledTimes(1)", tests)


if __name__ == "__main__":
    unittest.main()
