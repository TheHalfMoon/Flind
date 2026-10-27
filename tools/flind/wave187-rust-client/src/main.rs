//! Original Flind generated Rust Protobuf client to the actual Node gRPC server.
//! Synthetic test only; NOT the running Rust Kafka ingestion-consumer service.
use ingestion_worker_proto::ingestion::worker::v1::{
    ingest_stream_request, ingest_stream_response,
    worker_ingest_client::WorkerIngestClient, IngestStreamRequest,
    KafkaMessage, StreamHello, SubBatch, SubBatchStatus,
};
use std::{collections::HashMap, error::Error, time::Duration};
use tonic::transport::Endpoint;
fn hello() -> IngestStreamRequest {
    IngestStreamRequest { msg: Some(ingest_stream_request::Msg::Hello(StreamHello {
        consumer_id: "flind-wave187-rust-proto".into(), stream_epoch: 1,
    })) }
}
fn batch(seq: u64, offset: i64) -> IngestStreamRequest {
    let msg = KafkaMessage {
        topic: "flind_wave187_rust_proto".into(), partition: 0, offset,
        timestamp: 1761500000000, key: Some("flind:synthetic".into()),
        value: Some(r#"{"uuid":"00000000-0000-4000-8000-000000000187","event":"$pageview"}"#.into()),
        headers: HashMap::new(),
    };
    IngestStreamRequest { msg: Some(ingest_stream_request::Msg::SubBatch(SubBatch {
        seq, batch_id: "flind-wave187-synthetic".into(), messages: vec![msg],
        replay: false, assignment_epoch: 1, soft_budget_ms: 0,
    })) }
}
async fn exchange(port: u16, frames: Vec<IngestStreamRequest>)
 -> Result<(bool, bool, bool), Box<dyn Error>> {
    let mut client = WorkerIngestClient::new(
        Endpoint::from_shared(format!("http://127.0.0.1:{port}"))?
            .connect_timeout(Duration::from_secs(6)).connect().await?);
    let result = tokio::time::timeout(Duration::from_secs(8),
        client.ingest_stream(tokio_stream::iter(frames))).await??;
    let mut stream = result.into_inner();
    let mut ready = false; let mut ack = false; let mut error = false;
    loop {
        match tokio::time::timeout(Duration::from_secs(8), stream.message()).await? {
            Ok(Some(m)) => match m.msg {
                Some(ingest_stream_response::Msg::Ready(_)) => ready = true,
                Some(ingest_stream_response::Msg::Ack(a)) => {
                    ack |= a.seq == 1 && a.status == SubBatchStatus::Ok as i32
                        && a.accepted == 1 && a.unfinished.is_empty();
                },
                _ => {}
            },
            Ok(None) => break,
            Err(_) => {error = true; break}
        }
    }
    Ok((ready,ack,error))
}
#[tokio::main(flavor="multi_thread",worker_threads=2)]
async fn main() -> Result<(),Box<dyn Error>> {
    let port = std::env::var("FLIND_WAVE187_NODE_PORT")?.parse::<u16>()?;
    if port == 0 { return Err("invalid synthetic port".into()); }
    let (ready,ack,error) = exchange(port,vec![hello(),batch(1,187)]).await?;
    if !ready || !ack || error {return Err("native Rust protobuf → Node ACK not qualified".into());}
    let (ready2,ack2,error2) = exchange(port,vec![hello(),batch(2,188)]).await?;
    if !ready2 || ack2 || !error2 {return Err("bad Rust sequence not refused".into());}
    println!("{}",r#"{"phase":"original_rust_proto_to_original_node_grpc","original_rust_proto_client_wire_pass":true,"real_node_http2_ack_verified":true,"bad_rust_seq_refused":true,"production_rust_ingestion_consumer_qualified":false,"production_node_driver_qualified":false,"durable_clickhouse_qualified":false,"release_qualified":false}"#);
    Ok(())
}
