"""Regression guards for Kafka v1 offset safety; no broker required."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONSUMER = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.ts"
GATE = ROOT / "nodejs/src/common/kafka/consumer/offset-commit-gate.ts"


class OffsetSafetyWave88(unittest.TestCase):
    def test_v1_no_longer_stores_offsets_in_unconditional_finally(self):
        source = CONSUMER.read_text(encoding="utf-8")
        self.assertNotIn("void backgroundTask.finally(async () => {", source)
        self.assertIn("this.offsetCommitGate.observe(backgroundTask, () => {", source)
        self.assertIn("this.storeOffsetsForMessages(topicPartitionOffsetsToCommit)", source)
        self.assertIn("void backgroundTask.then(completeBackgroundTask, completeBackgroundTask)", source)

    def test_failure_is_fatal_to_consumer_loop_and_shutdown_waits_for_stores(self):
        source = CONSUMER.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("this.offsetCommitGate.failed"), 3)
        self.assertEqual(source.count("await this.offsetCommitGate.drain()"), 2)
        self.assertIn("refusing to acknowledge subsequent offsets", source)

    def test_gate_always_observes_rejections_and_orders_offset_stores(self):
        source = GATE.read_text(encoding="utf-8")
        self.assertIn("const completed = task.then(", source)
        self.assertIn("this.poisoned = true", source)
        self.assertIn("const following = this.tail.then(async () => {", source)
        self.assertIn("if (!this.poisoned && succeeded)", source)
        self.assertIn("this.tail = following.catch(", source)


if __name__ == "__main__":
    unittest.main()
