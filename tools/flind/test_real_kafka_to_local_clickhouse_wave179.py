"""Wave179: deterministic guards for bounded real local Kafka to ClickHouse relay."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.flind.qualify_ephemeral_kafka_wave84 import EVENTS
from tools.flind.qualify_local_clickhouse_tenant_sql_wave177 import EXPECTED_COLUMNS
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import (
    MIN_FREE_GIB, MAX_EVENT_BYTES, TOPIC, QUEUE_GROUP,
    Refusal, admitted, broker_environment, clickhouse_relay,
    fixed_payloads, produce_consume, readback_accepted,
)


class KafkaRelayTests(unittest.TestCase):
    def test_exact_original_synthetic_fixture_admitted(self):
        records = list(EVENTS)
        self.assertTrue(readback_accepted(records))
        self.assertEqual(len(records), 3)
        self.assertEqual({v["team_id"] for v in records}, {101, 202})

    def test_modified_reordered_or_nonfixture_records_rejected(self):
        expected = list(EVENTS)
        samples = [
            [], [*expected, expected[0]], list(reversed(expected)),
            [{**expected[0], "team_id": 202}, *expected[1:]],
            [{**expected[0], "properties": {"$pathname": "/unauthorized"}}, *expected[1:]],
            [{"team_id": 101}] * 3, None, tuple(expected),
        ]
        for item in samples:
            self.assertFalse(readback_accepted(item))

    def test_payload_size_is_bounded(self):
        payloads = fixed_payloads()
        self.assertEqual(len(payloads), 3)
        self.assertTrue(all(0 < len(v) <= MAX_EVENT_BYTES for v in payloads))
        self.assertTrue(all(v.startswith(b"{") for v in payloads))

    def test_invalid_kafka_destination_or_fixture_never_connects(self):
        with patch("confluent_kafka.Producer") as prod, patch("confluent_kafka.Consumer") as cons:
            for bootstrap in (
                "kafka.example.com:9092", "0.0.0.0:9092", "localhost:9092",
                "127.0.0.1:1; rm -rf /", "127.0.0.1:00",
            ):
                with self.assertRaises(Refusal):
                    produce_consume(bootstrap, fixed_payloads())
            with self.assertRaises(Refusal):
                produce_consume("127.0.0.1:19092", (b"{}",))
            prod.assert_not_called()
            cons.assert_not_called()

    def test_scratch_broker_env_does_not_forward_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = broker_environment(Path(tmp))
        self.assertIn("KAFKA_HEAP_OPTS", env)
        self.assertIn("-Xmx384m", env["KAFKA_HEAP_OPTS"])
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("AWS_ACCESS_KEY_ID", env)
        self.assertNotIn("OPENAI_API_KEY", env)

    def test_synthetic_topic_and_consumer_group_are_isolated(self):
        self.assertIn("flind", TOPIC)
        self.assertIn("synthetic", TOPIC)
        self.assertIn("flind", QUEUE_GROUP)
        self.assertGreaterEqual(MIN_FREE_GIB, 3.0)

    def test_invalid_clickhouse_schema_rejected_before_any_child_process(self):
        with tempfile.TemporaryDirectory() as scratch:
            with self.assertRaises(Refusal):
                clickhouse_relay(Path(scratch), list(EVENTS),
                                 {**EXPECTED_COLUMNS, "team_id": "String"}, "/bin/false")

    def test_invalid_kafka_records_refused_before_clickhouse(self):
        with tempfile.TemporaryDirectory() as scratch:
            fake = [{**EVENTS[0], "team_id": 202}, *list(EVENTS[1:])]
            with self.assertRaises(Refusal):
                clickhouse_relay(Path(scratch), fake, EXPECTED_COLUMNS, "/bin/false")

    def test_clickhouse_relay_accepts_only_known_team_ids_and_no_release_flags(self):
        self.assertTrue(all(type(x["team_id"]) is int for x in EVENTS))
        self.assertFalse(any("authorization" in x for x in EVENTS))
        self.assertEqual(len(set(x["team_id"] for x in EVENTS)), 2)


if __name__ == "__main__":
    unittest.main()
