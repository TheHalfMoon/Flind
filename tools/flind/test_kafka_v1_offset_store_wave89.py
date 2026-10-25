"""Wave 89: source-contract checks for Kafka v1 offset-store failure fencing."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.ts"
TESTS = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.test.ts"


class KafkaOffsetStoreWave89(unittest.TestCase):
    def _store_method(self) -> str:
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("private storeOffsetsForMessages = (")
        end = source.index("public async connect(", start)
        return source[start:end]

    def test_failed_storage_rethrows_after_logging_and_capture(self):
        body = self._store_method()
        self.assertIn("this.rdKafkaConsumer.offsetsStore(topicPartitionOffsetsToCommit)", body)
        catch = body.index("} catch (e) {")
        self.assertLess(catch, body.index("logger.error('📝', 'Failed to store offsets'"))
        self.assertLess(body.index("captureException(e)"), body.index("throw e"))
        self.assertIn("throw e", body)

    def test_rethrown_error_reaches_failure_latched_wave88_gate(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("this.offsetCommitGate.observe(backgroundTask, () => {", source)
        self.assertIn("this.storeOffsetsForMessages(topicPartitionOffsetsToCommit)", source)
        self.assertIn("if (this.offsetCommitGate.failed)", source)
        self.assertNotIn("void backgroundTask.finally(async () => {", source)

    def test_real_jest_regressions_cover_exception_and_later_offset_fence(self):
        tests = TESTS.read_text(encoding="utf-8")
        self.assertIn("describe('offset store failures (Wave 89)'", tests)
        self.assertIn("toThrow(storageFailure)", tests)
        self.assertIn("expect(gate.failed).toBe(true)", tests)
        self.assertIn("toHaveBeenCalledTimes(1)", tests)


if __name__ == "__main__":
    unittest.main()
