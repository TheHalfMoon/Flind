import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { Socket } from 'node:net'
import { gunzipSync } from 'node:zlib'
import test from 'node:test'
import { once } from 'node:events'

import { PostHog as FlindPostHog } from '@flind/node'
import { PostHog as PinnedPostHog } from 'posthog-node'

// Only synthetic event data. The HTTP server listens on a loopback address and
// never receives real project tokens or personally identifying information.
const API_TOKEN = 'phc_flind_wire_test_synthetic'
const EVENT_NAME = 'flind_node_sdk_wire_e2e'

// Fail closed before DNS or TCP connection creation. Restore the original method
// after each capture so unrelated test processes are unaffected.
function restrictSocketsToLoopback(port) {
    const original = Socket.prototype.connect
    Socket.prototype.connect = function (...args) {
        // net.createConnection() passes normalized [options, callback] as the
        // first argument to Socket.connect(); undici uses this form on Node 26.
        // Validate the actual destination, not the wrapper array.
        const first = Array.isArray(args[0]) ? args[0][0] : args[0]
        const options = typeof first === 'object' && first !== null
            ? first
            : { port: first, host: typeof args[1] === 'string' ? args[1] : undefined }
        // Never resolve a hostname: DNS/hosts-file changes could redirect it.
        const host = options.host ?? options.hostname
        if (Number(options.port) !== port || !['127.0.0.1', '::1'].includes(host)) {
            throw new Error('Flind wire test blocked outbound socket')
        }
        return original.apply(this, args)
    }
    return () => { Socket.prototype.connect = original }
}

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
    const restoreSockets = restrictSocketsToLoopback(address.port)
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
        restoreSockets()
        server.closeAllConnections()
        await new Promise((resolve) => server.close(resolve))
    }
}

function decodedEvent(packets) {
    assert.ok(packets.length > 0, 'SDK did not POST to the local HTTP server')
    // Reject extra local requests as well as missing capture requests. A valid
    // batch must not conceal unexpected SDK traffic to other local endpoints.
    for (const packet of packets) {
        assert.equal(packet.method, 'POST', 'SDK must not issue unexpected HTTP methods')
        assert.equal(packet.path, '/batch/', 'SDK must not contact unexpected local routes')
    }
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

test('Flind Node SDK CJS and ESM both reject absent or inherited collector origins before network use', async () => {
    const { createRequire } = await import('node:module')
    const require = createRequire(import.meta.url)
    const CjsSDK = require('@flind/node').PostHog
    const EsmSDK = (await import('@flind/node')).PostHog

    for (const Implementation of [CjsSDK, EsmSDK]) {
        for (const host of [
            undefined,
            '',
            'https://us.i.posthog.com',
            'https://us.posthog.com',
            'https://eu.posthog.com',
            'https://app.dev.posthog.dev',
            'http://collector.flind.example',
            'http://localhost:8010',
            'https://user:secret@collector.flind.example',
            'https://collector.flind.example/private',
            'https://collector.flind.example/?token=secret',
            'not-a-url',
        ]) {
            assert.throws(
                () => new Implementation(API_TOKEN, {
                    ...(host === undefined ? {} : { host }),
                    flushInterval: 0,
                    enableExceptionAutocapture: false,
                }),
                /explicit owned host|valid HTTPS origin|explicit safe, non-donor HTTPS origin/,
                `${Implementation.name}: ${host}`
            )
        }
    }
})

test('socket guard rejects non-loopback and incorrect-port connections before dialing', () => {
    const restore = restrictSocketsToLoopback(54321)
    try {
        assert.throws(() => new Socket().connect(443, 'example.com'), /blocked outbound socket/)
        assert.throws(() => new Socket().connect(54322, '127.0.0.1'), /blocked outbound socket/)
        assert.throws(() => new Socket().connect([{ host: 'example.com', port: 54321 }]), /blocked outbound socket/)
        assert.throws(() => new Socket().connect([{ host: '127.0.0.1', port: 54322 }]), /blocked outbound socket/)
        assert.throws(() => new Socket().connect([{ host: 'localhost', port: 54321 }]), /blocked outbound socket/)
        assert.throws(() => new Socket().connect([{ port: 54321 }]), /blocked outbound socket/)
    } finally {
        restore()
    }
})

test('wire validator rejects an event delivered to an incorrect ingestion path', () => {
    const invalidPacket = {
        method: 'POST',
        path: '/unexpected/',
        body: Buffer.from(JSON.stringify({
            api_key: API_TOKEN,
            batch: [{ event: EVENT_NAME, distinct_id: 'synthetic-local-user', properties: { flind_wire_test: true } }],
        })),
    }
    assert.throws(() => decodedEvent([invalidPacket]), /unexpected local routes/)
})

test('wire validator rejects extra local traffic even when a valid batch exists', () => {
    const validPacket = {
        method: 'POST', path: '/batch/',
        body: Buffer.from(JSON.stringify({
            api_key: API_TOKEN,
            batch: [{ event: EVENT_NAME, distinct_id: 'synthetic-local-user', properties: { flind_wire_test: true } }],
        })),
    }
    assert.throws(() => decodedEvent([validPacket, { ...validPacket, path: '/unexpected/' }]), /unexpected local routes/)
    assert.throws(() => decodedEvent([validPacket, { ...validPacket, method: 'GET' }]), /unexpected HTTP methods/)
})

test('private Flind Node SDK sends synthetic events to an explicitly local host', { timeout: 15000 }, async () => {
    decodedEvent(await captureLocally(FlindPostHog))
})

test('Flind Node SDK keeps pinned v5.63.2 capture wire parity', { timeout: 20000 }, async () => {
    const flind = decodedEvent(await captureLocally(FlindPostHog))
    const pinned = decodedEvent(await captureLocally(PinnedPostHog))
    assert.deepEqual(flind, pinned)
})
