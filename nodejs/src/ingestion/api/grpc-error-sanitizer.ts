/**
 * Error details from the native ingestion pipeline can include connection
 * strings, Kafka record metadata, tokens or private filesystem paths.
 * They belong in internal fatal reporting, never a WorkerIngest gRPC frame.
 */
export function safeIngestFailureMessage(cause: unknown): string {
    // Deliberately ignore the cause rather than relying on a regex blacklist.
    void cause
    return 'ingest pipeline failed'
}
