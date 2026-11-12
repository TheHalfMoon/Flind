import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { gunzipSync } from 'node:zlib'
import test from 'node:test'
import { once } from 'node:events'

import { PostHog as FlindPostHog } from '@flind/node'
import { PostHog as PinnedPostHog } from 'posthog-node'

// Only synthetic event data. The HTTP server listens on a loopback address and
// never receives real project tokens or personally identifying information.
const API_TOKEN = 'phc_flind_wire_test_synthetic'
const EVENT_NAME = 'flind_node_sdk_wire_e2e'

async function captureLocally(Implementation) {
    const packets = []
    const server = createServer(async (request, response) => {
        const chunks = []
        for await (const chunk of request) {
            chunks.push(chunk)
        }
        packets.push({
            method: request.method,
            path: request.url?.split('?')[0],
            body: Buffer.concat(chunks),
            encoding: request.headers['content-encoding'],
        })
        response.writeHead(200, { 'content-type': 'application/json' })
        response.end('{"status":1}')
    })
    server.listen(0, '127.0.0.1')
    await once(server, 'listening')
    const address = server.address()
    assert.ok(address && typeof address !== 'string')
    const client = new Implementation(API_TOKEN, {
        host: `http://127.0.0.1:${address.port}`,
        flushAt: 1,
        flushInterval: 0,
        maxRetries: 0,
        requestTimeout: 5000,
        enableExceptionAutocapture: false,
    })
    try {
        client.capture({
            distinctId: 'synthetic-local-user',
            event: EVENT_NAME,
            properties: { flind_wire_test: true },
        })
        await client.flush()
        await client.shutdown()
        return packets
    } finally {
        server.closeAllConnections()
        await new Promise((resolve) => server.close(resolve))
    }
}

function decodedEvent(packets) {
    assert.ok(packets.length > 0, 'SDK did not POST to the local HTTP server')
    const posts = packets.filter((p) => p.method === 'POST')
    assert.ok(posts.length > 0, 'SDK made no POST request')
    const candidates = posts.map((p) => {
        try {
            const decoded = p.encoding === 'gzip' ? gunzipSync(p.body) : p.body
            return { path: p.path, json: JSON.parse(decoded.toString('utf8')) }
        } catch {
            return null
        }
    }).filter(Boolean)
    const match = candidates.find((entry) => entry.json.batch?.some((event) => event.event === EVENT_NAME))
    assert.ok(match, `No synthetic event in local requests: ${JSON.stringify(posts.map((p) => ({ path: p.path, byteCount: p.body.length })))}`)
    // The ingestion route is part of the public HTTP contract. Comparing two
    // implementations alone would not catch the same route regression in both.
    assert.equal(match.path, '/batch/', 'SDK capture must use the documented batch ingestion route')
    assert.equal(match.json.api_key, API_TOKEN)
    const event = match.json.batch.find((item) => item.event === EVENT_NAME)
    assert.equal(event.distinct_id, 'synthetic-local-user')
    assert.equal(event.properties.flind_wire_test, true)
    return { path: match.path, event: event.event, distinct_id: event.distinct_id, api_key: match.json.api_key }
}

test('wire validator rejects an event delivered to an incorrect ingestion path', () => {
    const invalidPacket = {
        method: 'POST',
        path: '/unexpected/',
        body: Buffer.from(JSON.stringify({
            api_key: API_TOKEN,
            batch: [{ event: EVENT_NAME, distinct_id: 'synthetic-local-user', properties: { flind_wire_test: true } }],
        })),
    }
    assert.throws(() => decodedEvent([invalidPacket]), /documented batch ingestion route/)
})

test('private Flind Node SDK sends synthetic events to an explicitly local host', { timeout: 15000 }, async () => {
    decodedEvent(await captureLocally(FlindPostHog))
})

test('Flind Node SDK keeps pinned v5.63.2 capture wire parity', { timeout: 20000 }, async () => {
    const flind = decodedEvent(await captureLocally(FlindPostHog))
    const pinned = decodedEvent(await captureLocally(PinnedPostHog))
    assert.deepEqual(flind, pinned)
})
