import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { safeIngestFailureMessage } from '../../nodejs/src/ingestion/api/grpc-error-sanitizer.ts'

const reasons = [
    'hook failed: PRIVATE_KAFKA_TOKEN',
    'postgres://admin:SUPER_SECRET_PASSWORD@127.0.0.1:5432/test',
    'PRIVATE_EVENT_PAYLOAD',
    new Error('PRIVATE_EXCEPTION_MESSAGE'),
    { toString() { throw new Error('PRIVATE_TOSTRING_SECRET') } },
]
for (const reason of reasons) {
    assert.equal(safeIngestFailureMessage(reason), 'ingest pipeline failed')
}

const server = readFileSync(new URL('../../nodejs/src/ingestion/api/grpc-server.ts', import.meta.url), 'utf8')
const blockStart = server.indexOf('if (result.kind === \'at_capacity\')')
const blockEnd = server.indexOf('} finally {', blockStart)
assert.ok(blockStart > -1 && blockEnd > blockStart)
const rejection = server.slice(blockStart, blockEnd)

assert.ok(rejection.includes('const publicReason = safeIngestFailureMessage(result.reason)'))
assert.ok(rejection.includes('stream.acks.push(failedAck(seq, publicReason))'))
assert.ok(rejection.includes('grpcSubBatches.inc({ status: \'failed\' })'))
assert.ok(rejection.includes('throw new ConnectError(`sub-batch ${seq} rejected: ${publicReason}`, Code.Internal)'))
assert.equal(rejection.includes('failedAck(seq, result.reason)'), false)
assert.equal(rejection.includes('${result.reason}'), false)

const jest = readFileSync(new URL('../../nodejs/src/ingestion/api/grpc-server.test.ts', import.meta.url), 'utf8')
assert.ok(jest.includes("expect(collected.acks[0].error).toBe('ingest pipeline failed')"))
assert.ok(jest.includes("expect(collected.error!.message).not.toContain('PRIVATE_KAFKA_TOKEN')"))
console.log('Wave137 PASS: real sanitizer rejects secrets and both outgoing batch-error surfaces use it')
