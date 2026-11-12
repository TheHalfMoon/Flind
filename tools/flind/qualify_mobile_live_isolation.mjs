import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { liveStatsHost, fetchLiveStats } from '../../products/mobile/src/api/liveStatsHost.ts'

test('Flind mobile never derives an inherited or arbitrary live stats host', () => {
    for (const host of ['https://us.posthog.com', 'https://eu.posthog.com', 'https://flind.invalid', 'http://localhost:8000', '', 'not-a-url']) {
        assert.equal(liveStatsHost(host), null, host)
    }
})

test('live tokens cannot leave mobile via legacy stats fetch', async () => {
    const originalFetch = globalThis.fetch
    let invoked = 0
    globalThis.fetch = () => {
        invoked += 1
        throw new Error('Network must not be called')
    }
    try {
        await assert.rejects(fetchLiveStats('https://live.us.posthog.com', 'synthetic-secret'), /not configured/)
        await assert.rejects(fetchLiveStats('https://evil.example', 'synthetic-secret'), /not configured/)
        assert.equal(invoked, 0, 'no network or token egress')
    } finally {
        globalThis.fetch = originalFetch
    }
})

test('Live UI exports the fail-closed routing and preserves project-scoped query fallback', () => {
    const api = readFileSync(new URL('../../products/mobile/src/api/live.ts', import.meta.url), 'utf8')
    const hooks = readFileSync(new URL('../../products/mobile/src/features/live/hooks.ts', import.meta.url), 'utf8')
    assert.match(api, /export \{ liveStatsHost, fetchLiveStats, LiveStatsError \} from '\.\/liveStatsHost'/)
    assert.doesNotMatch(api, /live\.(?:us|eu)\.posthog\.com/)
    assert.match(hooks, /statsHost: liveStatsHost\(scope\.host\)/)
    assert.match(hooks, /host === null \|\| token === null \|\| failed/)
    assert.match(hooks, /liveQuery\('usersOnline'/)
    assert.match(hooks, /enabled: stats\.fallback/)
})
