"""Wave93: Kafka v1 consume-loop failure must never bypass native disconnect."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "nodejs/src/common/kafka/consumer/consumer-v1.ts"
HELPER = ROOT / "nodejs/src/common/kafka/consumer/consumer-loop-cleanup.ts"
TESTS = ROOT / "nodejs/src/common/kafka/consumer/consumer-loop-cleanup.test.ts"


class KafkaLoopCleanupWave93(unittest.TestCase):
    def test_loop_finally_uses_ordered_drain_then_native_close(self):
        code = V1.read_text(encoding="utf-8")
        a = code.index("const startConsuming = async (): Promise<void> => {")
        b = code.index("this.consumerLoop = startConsuming().catch(", a)
        loop = code[a:b]
        self.assertIn("await drainAndDisconnectConsumer(", loop)
        self.assertIn("this.offsetCommitGate,", loop)
        self.assertIn("() => this.disconnectConsumer(),", loop)
        self.assertIn("loopFailure", loop)
        self.assertNotIn("await Promise.all(this.backgroundTask.map((t) => t.promise))", loop)

    def test_helper_waits_all_and_preserves_processing_and_teardown_causes(self):
        code = HELPER.read_text(encoding="utf-8")
        self.assertIn("await Promise.allSettled(pending)", code)
        self.assertIn("await gate.drain()", code)
        self.assertIn("await disconnect()", code)
        self.assertIn("new AggregateError(failures, 'Kafka consumer loop and cleanup failed')", code)
        self.assertLess(code.index("await gate.drain()"), code.index("await disconnect()"))
        self.assertLess(code.index("await disconnect()"), code.index("throw failures[0]"))

    def test_helper_tracks_poisoned_commit_gate_even_if_no_task_is_pending(self):
        code = HELPER.read_text(encoding="utf-8")
        self.assertIn("if (gate.failed && failures.length === 0)", code)
        self.assertIn("result.status === 'rejected' && !failures.includes(result.reason)", code)

    def test_real_jest_regressions_for_original_and_cleanup_errors(self):
        tests = TESTS.read_text(encoding="utf-8")
        self.assertIn("Kafka v1 consumer loop cleanup (Wave 93)", tests)
        self.assertIn("retains both failed background processing and failed Kafka disconnect", tests)
        self.assertIn("reports poisoned offsets", tests)
        self.assertIn("never attempts disconnect before pending work", tests)


if __name__ == "__main__":
    unittest.main()
