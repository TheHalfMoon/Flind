import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const root = new URL('../../', import.meta.url)
const read = (path) => readFileSync(new URL(path, root), 'utf8')
const gate = read('frontend/src/lib/components/PayGateMini/payGateMiniLogic.tsx')
const gateView = read('frontend/src/lib/components/PayGateMini/PayGateMini.tsx')
const tag = read('frontend/src/lib/components/ReleaseStageTag/ReleaseStageTag.tsx')
const behavior = read('frontend/src/lib/components/PayGateMini/payGateMiniLogic.test.ts')

test('unconfigured Cloud/sales actions cannot send Flind users to donor SaaS', () => {
    assert.doesNotMatch(gate, /(?:https:\/\/us\.posthog\.com\/signup|sales@posthog\.com)/)
    assert.match(gate, /gateVariant === 'contact-sales' \|\| gateVariant === 'move-to-cloud'/)
    assert.match(gate, /return undefined/)
    assert.match(gate, /Cloud upgrades are not available from this Flind deployment/)
    assert.match(gate, /Flind sales contact is not configured for this deployment/)
    assert.match(gate, /return `\/organization\/billing/)
    assert.match(behavior, /disables inherited Cloud signup on self-hosted Flind/)
    assert.match(behavior, /ctaLink: undefined/)
})

test('self-hosted gate message is accurate and remains gated', () => {
    assert.match(gateView, /This feature is not available in this Flind deployment/)
    assert.doesNotMatch(gateView, /This feature is only available on Flind Cloud/)
    assert.match(gate, /return 'Unavailable here'/)
})

test('staff feature-flag link uses current Flind instance, not donor project 2', () => {
    assert.doesNotMatch(tag, /POSTHOG_PROJECT_URL|us\.posthog\.com\/project\/2/)
    assert.match(tag, /import \{ urls \} from 'scenes\/urls'/)
    assert.match(tag, /to=\{\u0060\$\{urls\.featureFlags\(\)\}\?search=\$\{encodeURIComponent\(product\.flag\)\}\u0060\}/)
})
