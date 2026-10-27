#!/usr/bin/env python3
"""Wave190: real Kafka->native rdkafka test consumer->original Node gRPC->
ClickHouse25.12 MergeTree disk restart, then ACK and synchronous Kafka commit.
Production Flind Rust IngestionConsumer and Node batching driver are NOT used.
"""
from __future__ import annotations
import json,os,select,signal,subprocess,sys,time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.flind.qualify_real_kafka_to_local_clickhouse_wave179 import qualify as run_kafka
from tools.flind.qualify_real_kafka_durable_mergetree_wave189 import attested_supported_runtime
from tools.flind.qualify_actual_node_grpc_http2_wire_wave186 import (
    admitted,checked_dependencies,original_sources,
)
class Blocked(ValueError):pass

def native_ack_receipt_valid(data:object)->bool:
    if type(data) is not dict:return False
    return all((
        data.get("native_kafka_three_events") is True,
        data.get("original_rust_proto_node_http2_ack_three") is True,
        type(data.get("native_rust_committed_offset")) is int,
        data.get("native_rust_committed_offset")==3,
        data.get("production_rust_consumer_qualified") is False,
        data.get("production_node_pipeline_qualified") is False,
        data.get("release_qualified") is False,
    ))

def native_connection(bootstrap:str,node:Path,rust:Path,binary:Path,scratch:Path)->dict:
    server=None
    result={"test_chain_pass":False,"node_server_stopped":False}
    try:
        server=subprocess.Popen(
            ["node","dist/server-kafka-durable-wire.mjs"],cwd=node,
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,bufsize=1,start_new_session=True,
            env={**os.environ,"FLIND_WAVE190_CLICKHOUSE_BIN":str(binary),
                 "FLIND_WAVE190_CLICKHOUSE_STATE":str(scratch/"wave190-mergetree"),
                 "NODE_OPTIONS":""},
        )
        assert server.stdout
        read,_,_=select.select([server.stdout],[],[],12)
        if not read:raise Blocked("native_node_server_start_timeout")
        line=server.stdout.readline().strip()
        if len(line)>500:raise Blocked("oversized_node_grpc_listener")
        ready=json.loads(line)
        port=ready.get("port")
        if ready.get("phase")!="wave190_listening" or type(port) is not int or not 1024<=port<=65535:
            raise Blocked("invalid_firstparty_grpc_listener")
        exe=rust/"target/debug/flind-wave190-rust-kafka-to-node"
        if exe.is_symlink() or not exe.is_file():
            raise Blocked("native_original_rust_proto_kafka_fixture_missing")
        cmd=subprocess.run([str(exe)],cwd=rust,capture_output=True,stdin=subprocess.DEVNULL,
                           timeout=48,env={**os.environ,"FLIND_WAVE190_BROKER":bootstrap,
                                           "FLIND_WAVE190_PORT":str(port)})
        if cmd.returncode or len(cmd.stdout)>3000 or len(cmd.stderr)>3000:
            raise Blocked("actual_rust_kafka_proto_to_node_durable_ack_failed")
        receipt=json.loads(cmd.stdout)
        if not native_ack_receipt_valid(receipt):
            raise Blocked("native_rust_kafka_commit_after_ack_receipt_refused")
        result["native_rdkafka_commit_after_grpc_ack"]=True
        result["native_committed_offset"]=3
    except (Blocked,OSError,ValueError,subprocess.TimeoutExpired) as e:
        result["blocker"]=str(e) if isinstance(e,Blocked) else type(e).__name__
    finally:
        if server:
            if server.poll() is None:os.killpg(server.pid,signal.SIGTERM)
            try:server.wait(timeout=9)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=4)
            result["node_server_stopped"]=server.poll() is not None
            result["node_server_exit"]=server.returncode
            if server.stdout:
                try:result["node_shutdown_receipt"]=json.loads(server.stdout.read(1200).strip())
                except (ValueError,UnicodeError):pass
                server.stdout.close()
            if server.stderr:server.stderr.close()
    shutdown=result.get("node_shutdown_receipt") or {}
    state=scratch/"wave190-mergetree/store"
    result["test_chain_pass"]=all((
        result.get("native_rdkafka_commit_after_grpc_ack") is True,
        result.get("native_committed_offset")==3,
        result.get("node_server_exit")==0,
        shutdown.get("durable_three_reopened") is True,
        shutdown.get("accepted_batches")==1,
        state.is_dir(),
        any(p.name=="checksums.txt" for p in state.rglob("checksums.txt")),
    ))
    result["release_qualified"]=False
    result["production_rust_ingester_qualified"]=False
    result["production_node_batch_driver_qualified"]=False
    return result

def qualify(repo:Path,kafka_home:Path,node:Path,rust:Path,scratch:Path,
            compressed_asset:Path)->dict:
    report={
        "phase":"wave190_real_kafka_native_rdkafka_original_node_durable_testdriver",
        "real_kafka_native_rust_original_proto_node_clickhouse_test_chain":False,
        "production_rust_ingester_qualified":False,
        "production_node_batch_driver_qualified":False,
        "authenticated_tenant_isolation_qualified":False,
        "release_qualified":False,
    }
    try:
        marker=scratch/".flind-wave190-owner"
        if marker.is_symlink() or not marker.is_file() or marker.read_text()!="FLIND_WAVE190_TEST_CHAIN_V1\n":
            raise Blocked("unowned_wave190_scratch")
        admitted(repo,node,Path(__file__).resolve().parents[2])
        checked_dependencies(node)
        report["original_node_blob_sha1"]=original_sources(repo,node)
        binary,_=attested_supported_runtime(repo,scratch,compressed_asset)
        from tools.flind.qualify_actual_node_grpc_http2_wire_wave186 import original_blob
        original=Path("/private/tmp/flind-wave76-frontend")
        for rel in (
            "rust/ingestion-worker-proto/src/lib.rs",
            "rust/ingestion-worker-proto/build.rs",
            "proto/ingestion/worker/v1/worker.proto",
        ):
            _,payload=original_blob(repo,rel)
            if (original/rel).read_bytes()!=payload:
                raise Blocked("original_rust_proto_source_changed")
        report["original_rust_proto_source_attested"]=True
        test_binary=rust/"target/debug/flind-wave190-rust-kafka-to-node"
        if not test_binary.is_file() or test_binary.is_symlink():
            raise Blocked("native_rust_test_client_not_compiled")
        bridge=run_kafka(
            repo,kafka_home,scratch,clickhouse=str(binary),
            on_broker_ready=lambda broker,owned:native_connection(
                broker,node,rust,binary,scratch),
        )
        native=bridge.get("optional_private_kafka_probe") or {}
        report["kafka_431_broker_qualified"]=bridge.get("kafka_431_broker_qualified") is True
        report["kafka_cleanup_qualified"]=all((
            bridge.get("owned_kafka_process_stopped") is True,
            bridge.get("owned_kafka_scratch_removed") is True,
        ))
        report["synthetic_chain_grpc_and_disk_qualified"]=native.get("test_chain_pass") is True
        report["native_committed_offset"]=native.get("native_committed_offset")
        report["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"]=all((
            report["kafka_431_broker_qualified"],
            bridge.get("real_kafka_producer_ack_qualified") is True,
            bridge.get("real_kafka_consumer_qualified") is True,
            bridge.get("local_clickhouse_relay_qualified") is True,
            report["synthetic_chain_grpc_and_disk_qualified"],
            type(node_result.get("native_committed_offset")) is int,
            node_result.get("native_committed_offset")==3,
            node_result.get("node_server_stopped") is True,
            node_result.get("release_qualified") is False,
            node_result.get("production_rust_ingester_qualified") is False,
            node_result.get("production_node_batch_driver_qualified") is False,
            report["kafka_cleanup_qualified"],
        ))
        if not report["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"]:
            raise Blocked(native.get("blocker") or bridge.get("blocker")
                          or "native_chain_not_proven")
    except (Blocked,OSError,ValueError,subprocess.TimeoutExpired) as exc:
        report["blocker"]=str(exc) if isinstance(exc,Blocked) else type(exc).__name__
    return report

def main()->int:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("repo","kafka-home","node","rust","scratch","compressed-clickhouse"):
        p.add_argument("--"+flag,type=Path,required=True)
    a=p.parse_args()
    result=qualify(a.repo,a.kafka_home,a.node,a.rust,a.scratch,a.compressed_clickhouse)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result["real_kafka_native_rust_original_proto_node_clickhouse_test_chain"] else 2

if __name__=="__main__":
    raise SystemExit(main())
