import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { isInheritedProviderHostname } from '../../products/mobile/src/auth/hostSafety.ts'

const read = (name) => readFileSync(new URL('../../' + name, import.meta.url), 'utf8')

test('rejects inherited provider origin hostnames but no unrelated Flind hosts', () => {
    for (const host of ['posthog.com', 'us.posthog.com', 'EU.posthog.com', 'app.dev.posthog.dev', 'posthog.dev', 'posthog.com.']) {
        assert.equal(isInheritedProviderHostname(host), true, host)
    }
    for (const host of ['us.posthog.com.evil', 'posthog.example.com', 'flind.example', 'localhost']) {
        assert.equal(isInheritedProviderHostname(host), false, host)
    }
})

test('mobile sign-in only offers configured Flind identities', () => {
    const src = read('products/mobile/src/auth/regions.ts')
    assert.doesNotMatch(src, /https:\/\/(us|eu|app)\.posthog\.com/)
    assert.doesNotMatch(src, /a5TY7w9I|1A7vO138|DC5uRLVb/)
    assert.match(src, /validateHost\(region\.host, false\)/)
    assert.match(src, /isInheritedProviderHostname\(url\.hostname\)/)
    assert.match(src, /EXPO_PUBLIC_FLIND_US_HOST/)
    assert.match(src, /EXPO_PUBLIC_FLIND_EU_CLIENT_ID/)
})

test('no configured Flind cloud defaults to self-hosted sign-in', () => {
    const ui = read('products/mobile/src/auth/SignInScreen.tsx')
    assert.match(ui, /CLOUD_REGIONS\.length === 0 \|\|/)
    assert.match(ui, /CLOUD_REGIONS\.length > 0 \?/)
    assert.doesNotMatch(ui, /@PostHog/)
    assert.match(ui, />Flind<\/Text>/)
})
