/**
 * Only explicitly approved routing coordinates may enter Kafka operational
 * diagnostics. The producer/consumer native config is populated from
 * environment variables and can contain SASL credentials or TLS secrets.
 * Never spread or stringify that config into an ingestion log.
 */
export function safeKafkaLogContext(config: { topic: string; groupId: string }): {
    topic: string
    groupId: string
} {
    return { topic: config.topic, groupId: config.groupId }
}
