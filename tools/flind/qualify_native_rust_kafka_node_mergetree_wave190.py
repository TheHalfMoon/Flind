#!/usr/bin/env python3
"""Wave190: actual private Kafka -> native rdkafka client + original Flind proto ->
original Node WorkerIngestServer -> test-only durable ClickHouse MergeTree.
NOT production Rust consumer, real Node pipeline, authorization or release.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import json
import os
import select
import signal
import subprocess
import sys
import time

sys.path.insert(0, "/private/tmp/flind-wave164-runner")
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import qualify as kafka_qualify
from tools.flind.qualify_real_kafka_durable_mergetree_wave189 import attested_supported_runtime
from tools.flind import qualify_actual_node_grpc_http2_wire_wave186 as node_attest

REF = Path("/private/tmp/flind-wave171-current-boot")
KAFKA = Path("/private/tmp/flind-kafka-4.3.1/kafka_2.13-4.3.1")
SCRATCH = Path("/private/tmp/flind-wave190-integration")
CH_ASSET = Path("/private/tmp/flind-wave188-ch2512-durable/clickhouse-original-compressed-aarch64")
NODE = Path("/private/tmp/flind-wave186-grpc-core")
RUST = Path("/private/tmp/flind-wave190-rust-kafka-node/target/debug/flind-wave190-rust-kafka-to-node")
APPROVED_KEYS = ("native_kafka_three_events","original_rust_proto_node_http2_ack_three")
ROOT = Path(__file__).resolve().parents[2]
RUST_PROTO = (
 "rust/ingestion-worker-proto/src/lib.rs",
 "rust/ingestion-worker-proto/build.rs",
 "proto/ingestion/worker/v1/worker.proto",
)
NODE_TEST_FILES = (
 ("tools/flind/verify_native_kafka_node_durable_wave190.mjs","server-kafka-durable-wire.mjs"),
 ("tools/flind/build_native_kafka_node_durable_wave190.mjs","build-kafka-durable-wire.mjs"),
)
FORBIDDEN = ("production_rust_consumer_qualified","production_node_pipeline_qualified","release_qualified")
REPORT = {"actual_native_kafka_proto_node_durable_test_bridge_pass":False,
          "production_rust_consumer_qualified":False,
          "production_node_pipeline_qualified":False,
          "authenticated_tenant_isolation_qualified":False,
          "release_qualified":False}
def fail(value):
    raise ValueError(value)

def approved_native_receipt(data):
    return (type(data) is dict
        and all(data.get(key) is True for key in APPROVED_KEYS)
        and all(data.get(key) is False for key in FORBIDDEN)
        and type(data.get("native_rust_committed_offset")) is int
        and data["native_rust_committed_offset"]==3)

def approved_node_stop(data, exit_code):
    return (type(data) is dict and exit_code==0
        and data.get("phase")=="wave190_stopped"
        and data.get("durable_three_reopened") is True
        and type(data.get("accepted_batches")) is int
        and data["accepted_batches"]==1)

def verify_first_party_fixture():
    """Refuse stale original Rust proto source or changed tracked test harness."""
    node_attest.admitted(REF,NODE,ROOT)
    node_attest.checked_dependencies(NODE)
    original = Path("/private/tmp/flind-wave76-frontend")
    for relative in RUST_PROTO:
        _, blob = node_attest.original_blob(REF,relative)
        old = original / relative
        if not old.is_file() or old.is_symlink() or old.read_bytes()!=blob:
            fail("original_rust_proto_source_changed")
    manifest = ROOT/"tools/flind/wave190-rust-kafka-node/Cargo.toml"
    client = ROOT/"tools/flind/wave190-rust-kafka-node/src/main.rs"
    lock = ROOT/"tools/flind/wave190-rust-kafka-node/Cargo.lock"
    source_root = Path("/private/tmp/flind-wave190-rust-kafka-node")
    if any(x.is_symlink() or not x.is_file() for x in (manifest,client,lock)):
        fail("original_rust_fixture_missing")
    expected_manifest = manifest.read_text().replace(
        "../../../rust/ingestion-worker-proto",
        str(original/"rust/ingestion-worker-proto"))
    if ((source_root/"Cargo.toml").read_text()!=expected_manifest
        or (source_root/"src/main.rs").read_bytes()!=client.read_bytes()
        or (source_root/"Cargo.lock").read_bytes()!=lock.read_bytes()):
        fail("native_rust_fixture_modified")
    for rel,dest in NODE_TEST_FILES:
        p=ROOT/rel
        if not p.is_file() or p.is_symlink() or p.stat().st_size>12000:
            fail("untrusted_node_test_fixture")
        target=NODE/dest
        if target.is_symlink():fail("symlinked_node_scratch_fixture")
        target.write_bytes(p.read_bytes())

def scratch_prepare():
    if SCRATCH.is_symlink() or SCRATCH.exists():
        fail("wave190_test_scratch_already_exists")
    if (SCRATCH.parent.resolve()!=Path("/private/tmp").resolve()
            or not SCRATCH.name.startswith("flind-wave190-")):
        fail("unapproved_wave190_scratch_scope")
    SCRATCH.mkdir()
    (SCRATCH / ".flind-clickhouse-local-v1").write_text("FLIND_CLICKHOUSE_LOCAL_SCRATCH_V1\n")
    (SCRATCH / ".flind-wave189-owner").write_text("FLIND_WAVE189_DURABLE_KAFKA_V1\n")
    (SCRATCH / ".flind-wave190-owner").write_text("FLIND_WAVE190_KAFKA_RUST_NODE_DURABLE_V1\n")

def callback(broker, private, runtime):
    child={"actual_native_kafka_to_node_disk_readback_pass":False,
           "native_rust_commit_verified":False,
           "release_qualified":False}
    node=None
    try:
        if not (RUST.is_file() and RUST.stat().st_size>100000):
            fail("native_rust_client_missing_or_not_built")
        node=subprocess.Popen(
            ["node","dist/server-kafka-durable-wire.mjs"],cwd=NODE,
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,bufsize=1,start_new_session=True,
            env={**os.environ,"NODE_OPTIONS":"",
                 "FLIND_WAVE190_CLICKHOUSE_BIN":str(runtime),
                 "FLIND_WAVE190_CLICKHOUSE_STATE":str(SCRATCH/"wave190-mergetree-durable")},
        )
        if not node.stdout:fail("no_node_listener_stdout")
        ready,_,_=select.select([node.stdout],[],[],9)
        if not ready:fail("node_grpc_listen_timeout")
        line=node.stdout.readline()
        if len(line)>600:fail("oversized_node_listener")
        port=json.loads(line).get("port")
        if not (type(port) is int and 1024<=port<=65535):fail("invalid_original_node_listener")
        native=subprocess.run([str(RUST)],cwd=RUST.parent,
            stdin=subprocess.DEVNULL,capture_output=True,timeout=58,check=False,
            env={**os.environ,"FLIND_WAVE190_BROKER":broker,
                 "FLIND_WAVE190_PORT":str(port)})
        if native.returncode or len(native.stdout)>2200 or len(native.stderr)>2300:
            child["native_exit_code"]=native.returncode
            fail("native_rust_kafka_to_original_node_grpc_failed")
        receipt=json.loads(native.stdout)
        if not approved_native_receipt(receipt):
            fail("native_rust_kafka_to_node_commit_receipt_not_qualified")
        child["native_rust_commit_verified"]=True
        child["rust_exit_code"]=native.returncode
    except (ValueError,OSError,subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
        child["blocker"]=str(exc) if type(exc) is ValueError else type(exc).__name__
    finally:
        if node:
            if node.poll() is None:
                try:os.killpg(node.pid,signal.SIGTERM)
                except ProcessLookupError:pass
            try:node.wait(timeout=9)
            except subprocess.TimeoutExpired:
                try:os.killpg(node.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                node.wait(timeout=4)
            child["owned_node_stopped"]=node.poll() is not None
            child["node_exit_code"]=node.returncode
            if node.stdout:
                raw=node.stdout.read(1500)
                try:child["node_final_receipt"]=json.loads(raw.strip())
                except ValueError:child["node_final_receipt"]={}
                node.stdout.close()
            if node.stderr:node.stderr.close()
    receipt=child.get("node_final_receipt",{})
    child["actual_native_kafka_to_node_disk_readback_pass"]=bool(
        child["native_rust_commit_verified"]
        and child.get("owned_node_stopped") is True and child.get("node_exit_code")==0
        and approved_node_stop(receipt,child.get("node_exit_code")))
    if not child["actual_native_kafka_to_node_disk_readback_pass"]:
        child.setdefault("blocker","actual_node_disk_readback_or_shutdown_unqualified")
    return child

def main():
    start=time.monotonic()
    try:
        scratch_prepare()
        verify_first_party_fixture()
        REPORT["verified_original_node_source_hashes"]=node_attest.original_sources(REF,NODE)
        if not RUST.is_file():fail("rust_binary_missing")
        runtime,schema=attested_supported_runtime(REF,SCRATCH,CH_ASSET)
        REPORT["supported_clickhouse_runtime_verified"]=True
        script=NODE/"build-kafka-durable-wire.mjs"
        if not script.is_file():fail("missing_node_fixture_builder")
        builder=subprocess.run(["node",script.name],cwd=NODE,capture_output=True,
                               timeout=16,stdin=subprocess.DEVNULL,check=False)
        if builder.returncode or b"FLIND_WAVE190_ORIGINAL_NODE_SERVER_BUNDLE_PASS" not in builder.stdout:
            fail("node_source_attested_build_failed")
        report=kafka_qualify(REF,KAFKA,SCRATCH,clickhouse=str(runtime),
                on_broker_ready=lambda broker, private:callback(broker,private,runtime))
        child=report.get("optional_private_kafka_probe") or {}
        REPORT["child_receipt"]=child
        REPORT["real_kafka_broker_pass"]=report.get("kafka_431_broker_qualified") is True
        REPORT["owned_kafka_stopped"]=report.get("owned_kafka_process_stopped") is True
        REPORT["owned_kafka_scratch_removed"]=report.get("owned_kafka_scratch_removed") is True
        REPORT["actual_native_kafka_proto_node_durable_test_bridge_pass"]=all((
             report.get("real_kafka_producer_ack_qualified") is True,
             report.get("real_kafka_consumer_qualified") is True,
             report.get("local_clickhouse_relay_qualified") is True,
             child.get("actual_native_kafka_to_node_disk_readback_pass") is True,
             REPORT["owned_kafka_stopped"],REPORT["owned_kafka_scratch_removed"]))
        if not REPORT["actual_native_kafka_proto_node_durable_test_bridge_pass"]:
            REPORT["blocker"]=child.get("blocker") or report.get("blocker") or "native_full_synthetic_wire_failed"
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        REPORT["blocker"]=str(exc) if type(exc) is ValueError else type(exc).__name__
    REPORT["elapsed_seconds"]=round(time.monotonic()-start,1)
    print(json.dumps(REPORT,sort_keys=True,indent=2))
    return 0 if REPORT["actual_native_kafka_proto_node_durable_test_bridge_pass"] else 2
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch",type=Path,required=True)
    args=parser.parse_args()
    SCRATCH=args.scratch
    raise SystemExit(main())
