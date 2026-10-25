"""Wave 92: prevent short-circuit revocation of busy Kafka v1 partitions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.ts"
COORDINATOR = ROOT / "nodejs/src/common/kafka/consumer/revocation-safety.ts"
TESTS = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.test.ts"


class KafkaV1RebalanceWave92(unittest.TestCase):
    def _revocation(self) -> str:
        source = V1.read_text(encoding="utf-8")
        begin = source.index("public rebalanceCallback(")
        end = source.index("private completeRevocation(", begin)
        return source[begin:end]

    def test_no_first_rejection_short_circuit_during_partition_revocation(self):
        block = self._revocation()
        self.assertNotIn("Promise.all(this.backgroundTask.map((t) => t.promise))", block)
        self.assertIn("awaitRevocationSafety(pendingTasks, this.offsetCommitGate)", block)
        self.assertIn("const pendingTasks = this.backgroundTask.map((task) => task.promise)", block)

    def test_even_empty_background_list_drains_offset_gate_before_unassign(self):
        block = self._revocation()
        self.assertIn(".then(() => this.completeRevocation(assignments))", block)
        self.assertNotIn("if (this.backgroundTask.length > 0)", block)
        source = COORDINATOR.read_text(encoding="utf-8")
        self.assertIn("await Promise.allSettled(pending)", source)
        self.assertIn("await gate.drain()", source)
        self.assertLess(source.index("await gate.drain()"), source.index("return {"))

    def test_async_revocation_failure_is_observed_and_resets_local_bookkeeping(self):
        block = self._revocation()
        self.assertIn(".catch((error) => {", block)
        self.assertIn("this.resetRebalanceCoordination()", block)
        self.assertIn("offsetGateFailed", block)
        self.assertIn("failedTasks", block)

    def test_in_repo_jest_regressions_cover_pending_and_empty_batch_cases(self):
        tests = TESTS.read_text(encoding="utf-8")
        self.assertIn("rebalance waits for all background work (Wave 92)", tests)
        self.assertIn("synthetic earlier batch failed", tests)
        self.assertIn("incrementalUnassign).not.toHaveBeenCalled()", tests)
        self.assertIn("spyOn(gate, 'drain')", tests)


if __name__ == "__main__":
    unittest.main()
