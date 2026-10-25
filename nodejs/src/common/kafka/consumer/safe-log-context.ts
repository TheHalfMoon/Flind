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

/**
 * Native error objects (including Error.message and Error.stack) may embed
 * SASL passwords, OAuth bearer tokens, certificate material or broker URLs.
 * Export only bounded numeric error codes and boolean classifications.
 * Never coerce arbitrary native fields into diagnostic strings.
 */
export function safeKafkaErrorContext(error: unknown): {
    errorCode?: number
    errno?: number
    isFatal?: boolean
    isRetriable?: boolean
} {
    if ((typeof error !== 'object' || error === null) && typeof error !== 'function') {
        return {}
    }
    const object = error as Record<string, unknown>
    const read = (name: string): unknown => {
        try {
            return object[name]
        } catch {
            return undefined
        }
    }
    const result: {
        errorCode?: number
        errno?: number
        isFatal?: boolean
        isRetriable?: boolean
    } = {}
    const code = read('code')
    const errno = read('errno')
    const isFatal = read('isFatal')
    const isRetriable = read('isRetriable')
    if (typeof code === 'number' && Number.isSafeInteger(code)) {
        result.errorCode = code
    }
    if (typeof errno === 'number' && Number.isSafeInteger(errno)) {
        result.errno = errno
    }
    if (typeof isFatal === 'boolean') {
        result.isFatal = isFatal
    }
    if (typeof isRetriable === 'boolean') {
        result.isRetriable = isRetriable
    }
    return result
}
