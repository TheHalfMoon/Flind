import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/scenes/onboarding/sdks/sdk-install-instructions/nodejs.tsx', import.meta.url), 'utf8')

test('Node setup snippet instantiates the actual export of its installed package', () => {
    for (const command of ['npm install posthog-node', 'yarn add posthog-node', 'pnpm add posthog-node']) {
        assert.ok(source.includes(command), command)
    }
    assert.match(source, /import \{ PostHog \} from 'posthog-node'/)
    assert.match(source, /const client = new PostHog\(/)
    assert.doesNotMatch(source, /import \{ Flind \} from 'posthog-node'/)
    assert.doesNotMatch(source, /new Flind\(/)
})

test('snippet explicitly uses Flind current-origin host and never a provider cloud default', () => {
    assert.match(source, /import \{ apiHostOrigin \} from 'lib\/utils\/apiHost'/)
    assert.match(source, /host:.*apiHostOrigin\(\)/)
    assert.doesNotMatch(source, /(?:us|eu)\.i\.posthog\.com|https:\/\/app\.posthog\.com/)
    assert.match(source, /currentTeam\?\.api_token \?\? 'YOUR_PROJECT_API_KEY'/)
    assert.ok(source.includes('await client.shutdown()'))
})

test('exception-autocapture snippet option is still supported', () => {
    assert.match(source, /enableExceptionAutocapture = false/)
    assert.match(source, /options\.push\('enableExceptionAutocapture: true'\)/)
    assert.match(source, /options\.join/)
})
