//! Synthetic Wave190: actual Kafka via native rdkafka -> original Flind Rust
//! Protobuf -> actual Node WorkerIngestServer; not the production consumer.
use ingestion_worker_proto::ingestion::worker::v1::{
    ingest_stream_request, ingest_stream_response,
    worker_ingest_client::WorkerIngestClient, IngestStreamRequest,
    KafkaMessage, StreamHello, SubBatch, SubBatchStatus,
};
use rdkafka::{ClientConfig, Offset, TopicPartitionList};
use rdkafka::consumer::{BaseConsumer, CommitMode, Consumer};
use rdkafka::message::Message;
use std::{collections::HashMap, error::Error, time::{Duration, Instant}};
use tonic::transport::Endpoint;
const TOPIC: &str = "flind_wave179_synthetic_only";
const FIXTURES: [&str; 3] = [
    r#"{"distinct_id":"user-one","event":"$pageview","properties":{"$pathname":"/home"},"team_id":101}"#,
    r#"{"distinct_id":"user-one","event":"$pageview","properties":{"$pathname":"/private"},"team_id":202}"#,
    r#"{"distinct_id":"user-one","event":"purchase","properties":{"$pathname":"/pricing"},"team_id":101}"#,
];
#[tokio::main(flavor="multi_thread", worker_threads=2)]
async fn main() -> Result<(),Box<dyn Error>> {
    let broker=std::env::var("FLIND_WAVE190_BROKER")?;
    let port: u16=std::env::var("FLIND_WAVE190_PORT")?.parse()?;
    if !broker.starts_with("127.0.0.1:") || port==0 {return Err("nonlocal address refused".into());}
    let consumer: BaseConsumer=ClientConfig::new()
        .set("bootstrap.servers",&broker)
        .set("group.id","flind-wave190-native-rdkafka-durable")
        .set("auto.offset.reset","earliest")
        .set("enable.auto.commit","false")
        .set("enable.auto.offset.store","false").create()?;
    consumer.subscribe(&[TOPIC])?;
    let mut records=Vec::new();
    let deadline=Instant::now()+Duration::from_secs(24);
    while records.len()<3 && Instant::now()<deadline {
        if let Some(message)=consumer.poll(Duration::from_millis(350)) {
            let m=message?;
            let value=std::str::from_utf8(m.payload().ok_or("Kafka tombstone")?)?;
            let i=records.len();
            if value!=FIXTURES[i] || m.topic()!=TOPIC || m.partition()!=0
               || m.offset()!=i as i64 {return Err("unexpected Kafka fixture".into());}
            records.push(KafkaMessage {
                topic:TOPIC.to_owned(), partition:0, offset:m.offset(),
                timestamp:1761500000000,
                key:m.key().map(|b|String::from_utf8_lossy(b).into_owned()),
                value:Some(value.to_string()), headers:HashMap::new(),
            });
        }
    }
    if records.len()!=3 {return Err("Kafka fixture incomplete".into());}
    let endpoint=Endpoint::from_shared(format!("http://127.0.0.1:{port}"))?
       .connect_timeout(Duration::from_secs(5));
    let mut client=WorkerIngestClient::new(endpoint.connect().await?);
    let hello=IngestStreamRequest { msg:Some(ingest_stream_request::Msg::Hello(
        StreamHello {consumer_id:"flind-wave190-native-rdkafka".into(),stream_epoch:1}
    ))};
    let batch=IngestStreamRequest {msg:Some(ingest_stream_request::Msg::SubBatch(
        SubBatch {seq:1,batch_id:"flind-wave190-durable-test".into(),
        messages:records,replay:false,assignment_epoch:1,soft_budget_ms:0}
    ))};
    let response=tokio::time::timeout(Duration::from_secs(25),
        client.ingest_stream(tokio_stream::iter(vec![hello,batch]))).await??;
    let mut stream=response.into_inner();
    let mut ready=false;
    let mut ack=false;
    loop {
        match tokio::time::timeout(Duration::from_secs(23),stream.message()).await? {
            Ok(Some(m))=>match m.msg {
                Some(ingest_stream_response::Msg::Ready(_))=>ready=true,
                Some(ingest_stream_response::Msg::Ack(a))=>{
                    ack |= a.seq==1 && a.status==SubBatchStatus::Ok as i32
                        && a.accepted==3 && a.unfinished.is_empty();
                }
                _=>{},
            },
            Ok(None)=>break,
            Err(_)=>return Err("real Node returned gRPC stream error".into()),
        }
    }
    if !ready || !ack {return Err("durable acknowledgment not verified".into());}
    // No Kafka commit is allowed until Node gRPC sent the ACK *after*
    // its test driver reopened ClickHouse and compared all three UUIDs.
    let mut tp=TopicPartitionList::new();
    tp.add_partition_offset(TOPIC,0,Offset::Offset(3))?;
    consumer.commit(&tp,CommitMode::Sync)?;
    let committed=consumer.committed(Duration::from_secs(7))?;
    let partition=committed.find_partition(TOPIC,0).ok_or("Kafka commit not found")?;
    if partition.offset()!=Offset::Offset(3) {
        return Err("Kafka committed offset differs from durable frontier".into());
    }
    println!("{}",r#"{"native_kafka_three_events":true,"original_rust_proto_node_http2_ack_three":true,"native_rust_committed_offset":3,"production_rust_consumer_qualified":false,"production_node_pipeline_qualified":false,"release_qualified":false}"#);
    Ok(())
}
