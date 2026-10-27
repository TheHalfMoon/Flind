"""Wave189: real Kafka-to-MergeTree synthetic bridge fail-closed guardrails."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.flind import qualify_real_kafka_durable_mergetree_wave189 as w


class KafkaDurableGuard(unittest.TestCase):
    def test_real_first_party_kafka_fixture_is_only_accepted_input(self):
        self.assertEqual(len(w.EVENTS), 3)
        rows = w.kafka_record_projection(list(w.EVENTS))
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["team_id"] for row in rows}, {101, 202})
        self.assertEqual(len({row["uuid"] for row in rows}), 3)

    def test_changed_or_reordered_fixture_fails_closed(self):
        with self.assertRaises(w.Refused):
            w.kafka_record_projection(list(reversed(w.EVENTS)))
        bad = [dict(item) for item in w.EVENTS]
        bad[0]["team_id"] = 303
        with self.assertRaises(w.Refused):
            w.kafka_record_projection(bad)

    def test_clickhouse_process_budget_two(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave189-unit-", dir="/private/tmp") as td:
            root=Path(td)
            for ordinal in (0,3,-1):
                with self.assertRaisesRegex(w.Refused,"clickhouse_two_process_budget"):
                    w.ch_process(Path("/bin/echo"),root,root/"state","SELECT 1",ordinal)

    def test_refuses_existing_clickhouse_output_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave189-unit-", dir="/private/tmp") as td:
            root=Path(td)
            file=root/"wave189-clickhouse-1.jsonl"
            file.write_text("existing")
            with patch.object(w.subprocess,"run") as process:
                with self.assertRaisesRegex(w.Refused,"unowned_clickhouse_output_conflict"):
                    w.ch_process(Path("/bin/echo"),root,root/"state","SELECT 1",1)
                process.assert_not_called()
            self.assertEqual(file.read_text(),"existing")

    def test_unmarked_scratch_never_runs_clickhouse(self):
        with tempfile.TemporaryDirectory(prefix="flind-wave189-unit-", dir="/private/tmp") as td:
            root=Path(td)
            with patch.object(w,"checked_scratch"), patch.object(w.subprocess,"run") as process:
                with self.assertRaisesRegex(w.Refused,"unowned_wave189_scratch"):
                    w.attested_supported_runtime(Path("/fake"),root,Path("/fake"))
                process.assert_not_called()

    def test_clickhouse_real_readback_must_match_all_kafka_uuids(self):
        records=list(w.EVENTS)
        expected=w.kafka_record_projection(records)
        with tempfile.TemporaryDirectory(prefix="flind-wave189-unit-", dir="/private/tmp") as td:
            root=Path(td)
            session=root/"wave189-mergetree-state"
            def fake_process(binary, folder, store, sql, stage):
                if stage==1:
                    part=session/"store"/"a"/"checksums.txt"
                    part.parent.mkdir(parents=True)
                    part.write_text("test fixture")
                    return [{"team_id":101,"event_count":2},{"team_id":202,"event_count":1}]
                if stage==2:
                    return [
                        {"team_id":101,"event_count":2},
                        {"team_id":202,"event_count":1},
                        *sorted(({k:item[k] for k in ("uuid","team_id","event")} for item in expected),
                                key=lambda x:x["uuid"]),
                    ]
                raise AssertionError("unsupported stage")
            with patch.object(w,"ch_process",side_effect=fake_process) as cli:
                report=w.disk_persist_and_reopen(Path("/fake"),root,w.EXPECTED_COLUMNS,records)
            self.assertEqual(cli.call_count,2)
            self.assertTrue(report["kafka_mergetree_same_uuids_verified_after_restart"])
            self.assertFalse(report["release_qualified"])

    def test_bad_disk_readback_fails_closed(self):
        records=list(w.EVENTS)
        with tempfile.TemporaryDirectory(prefix="flind-wave189-unit-", dir="/private/tmp") as td:
            root=Path(td)
            def fake_process(binary,folder,store,sql,stage):
                if stage==1:return [{"team_id":101,"event_count":2},{"team_id":202,"event_count":1}]
                return [{"team_id":101,"event_count":2},{"team_id":202,"event_count":1},
                        {"uuid":"00000000-0000-4000-8000-000000000999","team_id":101,"event":"forged"}]
            with patch.object(w,"ch_process",side_effect=fake_process):
                with self.assertRaisesRegex(w.Refused,"kafka_durable_restart_uuid_mismatch"):
                    w.disk_persist_and_reopen(Path("/fake"),root,w.EXPECTED_COLUMNS,records)

    def simulate_kafka_consumer(self):
        class Message:
            def __init__(self,obj):self.obj=obj
            def error(self):return None
            def value(self):return json.dumps(self.obj).encode("utf8")
        class Consumer:
            instances=[]
            def __init__(self,config):
                self.config=config;self.messages=[Message(x) for x in w.EVENTS]
                self.commits=0;self.closed=False
                Consumer.instances.append(self)
            def subscribe(self,topics):self.topics=topics
            def poll(self,seconds):
                return self.messages.pop(0) if self.messages else None
            def commit(self,asynchronous=False):
                self.commits+=1
            def close(self):self.closed=True
        return Consumer

    def test_persistence_failure_never_commits_consumer_offsets(self):
        Consumer=self.simulate_kafka_consumer()
        with patch.dict(sys.modules,{"confluent_kafka":SimpleNamespace(Consumer=Consumer)}), patch.object(
            w,"disk_persist_and_reopen",side_effect=w.Refused("durable_sql_failed")
        ):
            report=w.callback("127.0.0.1:19092",Path("/fake"),Path("/fake"),w.EXPECTED_COLUMNS)
        self.assertFalse(report["kafka_durable_relay_and_offset_commit_pass"])
        self.assertFalse(report["actual_kafka_offset_committed_after_disk_readback"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual(report["blocker"],"durable_sql_failed")
        self.assertEqual(Consumer.instances[0].commits,0)
        self.assertTrue(Consumer.instances[0].closed)

    def test_forged_empty_success_receipt_never_commits_offset(self):
        Consumer=self.simulate_kafka_consumer()
        with patch.dict(sys.modules,{"confluent_kafka":SimpleNamespace(Consumer=Consumer)}), patch.object(
            w,"disk_persist_and_reopen",return_value={}
        ):
            report=w.callback("127.0.0.1:19092",Path("/fake"),Path("/fake"),w.EXPECTED_COLUMNS)
        self.assertEqual(report["blocker"],"durable_clickhouse_readback_receipt_not_verified")
        self.assertFalse(report["kafka_durable_relay_and_offset_commit_pass"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual(Consumer.instances[0].commits,0)
        self.assertTrue(Consumer.instances[0].closed)

    def test_successful_disk_readback_commits_only_once(self):
        Consumer=self.simulate_kafka_consumer()
        with patch.dict(sys.modules,{"confluent_kafka":SimpleNamespace(Consumer=Consumer)}), patch.object(
            w,"disk_persist_and_reopen",return_value={
                "kafka_consumed_records_persisted":3,
                "two_independent_clickhouse_processes_qualified":True,
                "kafka_mergetree_same_uuids_verified_after_restart":True,
                "native_rust_worker_qualified":False,
                "node_production_pipeline_qualified":False,
                "release_qualified":False,
            }
        ):
            report=w.callback("127.0.0.1:19092",Path("/fake"),Path("/fake"),w.EXPECTED_COLUMNS)
        self.assertTrue(report["kafka_durable_relay_and_offset_commit_pass"])
        self.assertEqual(Consumer.instances[0].commits,1)
        self.assertTrue(Consumer.instances[0].closed)
        self.assertFalse(report["release_qualified"])

    def test_parent_success_never_promotes_native_or_product_release(self):
        parent = {
            "kafka_431_broker_qualified":True,
            "real_kafka_producer_ack_qualified":True,
            "real_kafka_consumer_qualified":True,
            "local_clickhouse_relay_qualified":True,
            "owned_kafka_process_stopped":True,
            "owned_kafka_scratch_removed":True,
            "optional_private_kafka_probe":{
                "kafka_durable_relay_and_offset_commit_pass":True,
                "actual_kafka_offset_committed_after_disk_readback":True,
                "kafka_consumed_records_persisted":3,
            },
        }
        with patch.object(w,"attested_supported_runtime",return_value=(Path("/fake"),w.EXPECTED_COLUMNS)),patch.object(
            w,"real_kafka",return_value=parent
        ):
            result=w.qualify(Path("/fake"),Path("/fake"),Path("/fake"),Path("/fake"))
        self.assertTrue(result["real_kafka_to_durable_mergetree_relay_qualified"])
        for flag in ("real_first_party_rust_consumer_qualified","real_node_production_driver_qualified",
                     "authenticated_tenant_isolation_qualified","sdk_api_dashboard_qualified",
                     "release_qualified"):
            self.assertFalse(result[flag])


if __name__ == "__main__":
    unittest.main()
