import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

import { ownedAnalyticsHost } from '../../products/mobile/src/lib/mobileAnalyticsHost.ts'

test('mobile analytics has no default cloud host and accepts only explicit HTTPS origins', () => {
    for (const value of [undefined, '', 'not a URL', 'https://us.i.posthog.com', 'https://eu.posthog.com',
        'https://app.dev.posthog.dev', 'https://user:secret@analytics.flind.example',
        'http://analytics.flind.example', 'https://analytics.flind.example/path',
        'https://analytics.flind.example/?key=value', 'https://analytics.flind.example#fragment']) {
        assert.equal(ownedAnalyticsHost(value), null, String(value))
    }
    assert.equal(ownedAnalyticsHost('https://analytics.flind.example/'), 'https://analytics.flind.example')
    assert.equal(ownedAnalyticsHost('https://us.i.posthog.com.evil'), 'https://us.i.posthog.com.evil')
})

test('SDK initializer cannot read inherited key, host, replay or handoff configuration', () => {
    const src = readFileSync(new URL('../../products/mobile/src/lib/posthogClient.ts', import.meta.url), 'utf8')
    assert.doesNotMatch(src, /EXPO_PUBLIC_POSTHOG_(?:KEY|HOST|REPLAY|HANDOFF)/)
    assert.doesNotMatch(src, /DEFAULT_HOST|us\.i\.posthog\.com/)
    assert.match(src, /EXPO_PUBLIC_FLIND_ANALYTICS_KEY/)
    assert.match(src, /EXPO_PUBLIC_FLIND_ANALYTICS_HOST/)
    assert.match(src, /if \(!apiKey \|\| !host \|\| initialized\)/)
    assert.match(src, /host,\n\s*captureAppLifecycleEvents/)
})
