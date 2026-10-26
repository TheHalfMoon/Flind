import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { safeIngestFailureMessage } from '../../nodejs/src/ingestion/api/grpc-error-sanitizer.ts'

const dangerous = [
    Error('SECRET_KAFKA_TOKEN'),
    'PRIVATE_DATABASE_PASSWORD',
    { toString: () => { throw new Error('SECRET_THROW_FROM_TOSTRING') } },
    undefined,
    null,
]
for (const cause of dangerous) {
    assert.equal(safeIngestFailureMessage(cause), 'ingest pipeline failed')
}
const server = readFileSync(new URL('../../nodejs/src/ingestion/api/grpc-server.ts', import.meta.url), 'utf8')
assert.equal((server.match(/new ConnectError\(safeIngestFailureMessage\(error\), Code\.Internal\)/g) ?? []).length, 2)
assert.equal(server.includes('new ConnectError(String(error), Code.Internal)'), false)
assert.equal(server.includes('new ConnectError(`ingest pipeline failed: ${error.message}`, Code.Internal)'), false)

const jestSuite = readFileSync(new URL('../../nodejs/src/ingestion/api/grpc-server.test.ts', import.meta.url), 'utf8')
assert.ok(jestSuite.includes("expect(collected.error!.message).not.toContain('SECRET_INTERNAL_KEY')"))
assert.ok(jestSuite.includes("expect(onFatal).toHaveBeenCalledWith("))
console.log('Wave136 PASS: fatal/unknown WorkerIngest gRPC errors are sanitized at both callsites')
