"""Bounded native Kafka KRaft transport qualification guardrails."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tools.flind import qualify_ephemeral_kafka_wave84 as k


class IsolatedKafkaWave84(unittest.TestCase):
    def test_synthetic_payload_contains_colliding_identity_and_two_teams(self):
        events = [json.loads(line) for line in k.synthetic_messages().splitlines()]
        self.assertEqual(events, list(k.EVENTS))
        self.assertEqual(len(events), 3)
        self.assertEqual({ev["team_id"] for ev in events}, {101, 202})
        self.assertEqual(len({ev["distinct_id"] for ev in events}), 1)
        self.assertEqual(events[0]["properties"]["$pathname"], "/home")

    def test_config_has_only_private_loopback_addresses_and_temp_data(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "kafka"
            (home / "config").mkdir(parents=True)
            (home / "config/server.properties").write_text(
                "process.roles=broker,controller\n"
                "node.id=1\n"
                "controller.quorum.bootstrap.servers=localhost:9093\n"
                "listeners=PLAINTEXT://:9092,CONTROLLER://:9093\n"
                "advertised.listeners=PLAINTEXT://localhost:9092\n"
                "log.dirs=/tmp/kraft-combined-logs\n"
            )
            (root / "private").mkdir()
            output = k.isolated_config(home, root / "private", 12001, 12002)
            config = output.read_text()
            self.assertIn("listeners=PLAINTEXT://127.0.0.1:12001,CONTROLLER://127.0.0.1:12002", config)
            self.assertIn("advertised.listeners=PLAINTEXT://127.0.0.1:12001", config)
            self.assertIn("controller.quorum.bootstrap.servers=127.0.0.1:12002", config)
            self.assertIn(f"log.dirs={root}/private/data", config)
            self.assertIn("auto.create.topics.enable=false", config)
            self.assertNotIn("PLAINTEXT://:9092", config)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_config_rejects_nonprivate_or_duplicate_ports(self):
        for pair in ((0, 12002), (12001, 12001), (65536, 12002), (12001, True), ("1", 12002)):
            with self.subTest(pair=pair):
                with self.assertRaises(ValueError):
                    k.isolated_config(Path("/not-used"), Path("/tmp"), *pair)

    def test_config_rejects_missing_listeners_instead_of_using_broker_defaults(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "config").mkdir()
            (home / "config/server.properties").write_text("process.roles=broker,controller\nnode.id=1\n")
            with self.assertRaises(ValueError):
                k.isolated_config(home, home, 12001, 12002)

    def test_missing_local_binary_refused(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                k.kafka_paths(Path(tmp))

    @patch.object(k, "kafka_paths")
    @patch.object(k, "available_disk_gib", return_value=7.0)
    def test_disk_guard_prevents_touching_kafka(self, _, paths):
        report = k.qualify_kafka(Path("/not-used"))
        self.assertFalse(report["isolated_kafka_passed"])
        self.assertFalse(report["release_qualified"])
        paths.assert_not_called()

    @patch.object(k, "kafka_paths", side_effect=ValueError("missing"))
    @patch.object(k, "available_disk_gib", return_value=15.0)
    def test_missing_kafka_never_claims_success(self, _disk, _paths):
        report = k.qualify_kafka(Path("/not-used"))
        self.assertFalse(report["isolated_kafka_passed"])
        self.assertFalse(report["kafka_to_clickhouse_qualified"])

    def _mock_ready_fixture(self, *, consumer_result=None, topic_exit=0):
        path = Path("/synthetic-kafka")
        binaries = {name: path / ("kafka-" + name + ".sh") for name in
                    ("storage", "server-start", "topics", "console-producer", "console-consumer")}
        events = k.synthetic_messages()
        responses = [
            SimpleNamespace(returncode=0, stdout="4.3.1 (Commit:synthetic)\n"),
            SimpleNamespace(returncode=0, stdout="AbCdEfGhIjKlMnOpQrStUv\n"),
            SimpleNamespace(returncode=0, stdout="formatted"),
            SimpleNamespace(returncode=0, stdout=""),
            SimpleNamespace(returncode=topic_exit, stdout=""),
            SimpleNamespace(returncode=0, stdout=""),
            SimpleNamespace(returncode=0, stdout=events if consumer_result is None else consumer_result),
        ]
        return binaries, responses

    @patch.object(k, "available_disk_gib", return_value=15.0)
    @patch.object(k, "loopback_ports", return_value=(12001, 12002))
    @patch.object(k, "isolated_config")
    @patch.object(k, "kafka_paths")
    @patch.object(k, "_run")
    @patch.object(k.subprocess, "Popen")
    def test_exact_wire_roundtrip_and_broker_cleanup(
        self, popen, run, paths, conf, _ports, _disk
    ):
        binaries, responses = self._mock_ready_fixture()
        paths.return_value = binaries
        conf.return_value = Path("/synthetic-private/config")
        run.side_effect = responses
        broker = MagicMock()
        broker.poll.return_value = None
        popen.return_value = broker
        with patch.object(k.os, "killpg") as terminate:
            report = k.qualify_kafka(Path("/synthetic"))
        self.assertTrue(report["isolated_kafka_passed"])
        self.assertEqual(report["synthetic_events_published"], 3)
        self.assertEqual(report["synthetic_events_consumed"], 3)
        self.assertTrue(report["exact_json_message_roundtrip"])
        self.assertFalse(report["kafka_to_clickhouse_qualified"])
        self.assertFalse(report["release_qualified"])
        sent = run.call_args_list[5]
        self.assertEqual(sent.kwargs["text_input"], k.synthetic_messages())
        self.assertIn("acks=all", sent.args[0])
        self.assertIn("127.0.0.1:12001", str(sent.args[0]))
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["KAFKA_HEAP_OPTS"], "-Xms256m -Xmx512m")
        self.assertNotIn("KAFKA_OPTS", env)
        self.assertEqual(env["HOME"], env["TMPDIR"])
        self.assertNotEqual(env["HOME"], os.environ.get("HOME", ""))
        terminate.assert_called_once()
        broker.wait.assert_called_once()

    @patch.object(k, "available_disk_gib", return_value=15.0)
    @patch.object(k, "loopback_ports", return_value=(12001, 12002))
    @patch.object(k, "isolated_config", return_value=Path("/synthetic-private/config"))
    @patch.object(k, "kafka_paths")
    @patch.object(k, "_run")
    @patch.object(k.subprocess, "Popen")
    def test_optional_synthetic_relay_called_only_after_exact_broker_roundtrip(
        self, popen, run, paths, _conf, _ports, _disk
    ):
        binaries, responses = self._mock_ready_fixture()
        paths.return_value = binaries
        run.side_effect = responses
        broker = MagicMock()
        broker.poll.return_value = None
        popen.return_value = broker
        received = []

        def relay(records):
            received.append(records)
            return {"synthetic_relay_passed": True, "kafka_records_replayed": len(records)}

        with patch.object(k.os, "killpg"):
            report = k.qualify_kafka(Path("/synthetic"), on_consumed=relay)
        self.assertTrue(report["isolated_kafka_passed"])
        self.assertEqual(received, [tuple(k.EVENTS)])
        self.assertEqual(report["synthetic_relay"]["kafka_records_replayed"], 3)
        self.assertFalse(report["release_qualified"])
        broker.wait.assert_called_once()

    @patch.object(k, "available_disk_gib", return_value=15.0)
    @patch.object(k, "loopback_ports", return_value=(12001, 12002))
    @patch.object(k, "isolated_config", return_value=Path("/synthetic-private/config"))
    @patch.object(k, "kafka_paths")
    @patch.object(k, "_run")
    @patch.object(k.subprocess, "Popen")
    def test_tampered_consumption_never_invokes_synthetic_relay(
        self, popen, run, paths, _conf, _ports, _disk
    ):
        binaries, responses = self._mock_ready_fixture(
            consumer_result='{"event":"untrusted"}\n'
        )
        paths.return_value = binaries
        run.side_effect = responses
        broker = MagicMock()
        broker.poll.return_value = None
        popen.return_value = broker
        relay = MagicMock()
        with patch.object(k.os, "killpg"):
            report = k.qualify_kafka(Path("/synthetic"), on_consumed=relay)
        self.assertFalse(report["isolated_kafka_passed"])
        relay.assert_not_called()
        broker.wait.assert_called_once()

    @patch.object(k, "available_disk_gib", return_value=15.0)
    @patch.object(k, "loopback_ports", return_value=(12001, 12002))
    @patch.object(k, "isolated_config", return_value=Path("/synthetic-private/config"))
    @patch.object(k, "kafka_paths")
    @patch.object(k, "_run")
    @patch.object(k.subprocess, "Popen")
    def test_incorrect_consumer_message_fails_and_kills_private_broker(
        self, popen, run, paths, _conf, _ports, _disk
    ):
        binaries, responses = self._mock_ready_fixture(consumer_result='{"event":"tampered"}\n')
        paths.return_value = binaries
        run.side_effect = responses
        broker = MagicMock()
        broker.poll.return_value = None
        popen.return_value = broker
        with patch.object(k.os, "killpg") as terminate:
            report = k.qualify_kafka(Path("/synthetic"))
        self.assertFalse(report["isolated_kafka_passed"])
        self.assertFalse(report["release_qualified"])
        terminate.assert_called_once()
        broker.wait.assert_called_once()

    @patch.object(k, "available_disk_gib", return_value=15.0)
    @patch.object(k, "loopback_ports", return_value=(12001, 12002))
    @patch.object(k, "isolated_config", return_value=Path("/synthetic-private/config"))
    @patch.object(k, "kafka_paths")
    @patch.object(k, "_run")
    @patch.object(k.subprocess, "Popen")
    def test_topic_create_failure_prevents_publish_and_kills_broker(
        self, popen, run, paths, _conf, _ports, _disk
    ):
        binaries, responses = self._mock_ready_fixture(topic_exit=1)
        paths.return_value = binaries
        run.side_effect = responses
        broker = MagicMock()
        broker.poll.return_value = None
        popen.return_value = broker
        with patch.object(k.os, "killpg") as terminate:
            report = k.qualify_kafka(Path("/synthetic"))
        self.assertFalse(report["isolated_kafka_passed"])
        self.assertEqual(run.call_count, 5)
        terminate.assert_called_once()
        broker.wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
