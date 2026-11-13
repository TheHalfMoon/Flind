import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const root = new URL('../src/', import.meta.url)
const read = (path) => readFileSync(new URL(path, root), 'utf8')
const integrationDocs = {
    github: 'libraries/github',
    gitlab: 'error-tracking/integrations',
    jira: 'error-tracking/integrations',
    linear: 'error-tracking/integrations',
    slack: 'libraries/slack',
}

test('integration detail documentation links are operator-owned and conditional', () => {
    for (const [integration, path] of Object.entries(integrationDocs)) {
        const source = read('scenes/integrations/definitions/' + integration + '.tsx')
        assert.match(source, /import \{ flindDocsUrl \} from 'lib\/flindPublicLinks'/, integration)
        assert.ok(source.includes("docsUrl: flindDocsUrl('" + path + "') ?? undefined,"), integration)
        assert.doesNotMatch(source, /docsUrl:\s*['"]https?:\/\//, integration)
    }
})

test('GitHub description preserves in-app Slack navigation and avoids donor desktop installer', () => {
    const source = read('scenes/integrations/definitions/github.tsx')
    assert.match(source, /<Link to=\{urls\.integration\('slack'\)\}>Slack<\/Link>/)
    assert.match(source, /Flind Desktop connected/)
    assert.doesNotMatch(source, /posthog\.com\/desktop/)
})

test('Slack setup stays functional, documentation and banner avoid inherited provider', () => {
    const def = read('scenes/integrations/definitions/slack.tsx')
    const helper = read('lib/integrations/SlackIntegrationHelpers.tsx')
    assert.match(def, /PostConnect: SlackPostConnect/)
    assert.match(def, /useSetupUrl: useSlackSetupUrl/)
    assert.match(def, /useStatus: useSlackStatus/)
    assert.doesNotMatch(def, /res\.cloudinary\.com\/dmukukwp6/)
    assert.match(helper, /flindDocsUrl\('webhooks\/slack'\)/)
    assert.match(helper, /flindDocsUrl\('cdp\/destinations\/slack'\)/)
    assert.match(helper, /\{slackWebhookDocsUrl && \(/)
    assert.match(helper, /\{slackDestinationDocsUrl && \(/)
    assert.match(helper, /kind: 'slack'/)
    assert.doesNotMatch(helper, /posthog\.com\/docs/)
})

test('Twilio picker retains refresh and installation guidance with optional Flind help', () => {
    const source = read('lib/integrations/TwilioIntegrationHelpers.tsx')
    assert.match(source, /flindDocsUrl\('cdp\/destinations\/twilio'\)/)
    assert.match(source, /\{twilioDocsUrl && \(/)
    assert.match(source, /loadAllTwilioPhoneNumbers\(true\)/)
    assert.match(source, /No phone numbers found/)
    assert.doesNotMatch(source, /posthog\.com\/docs/)
})

test('optional URLs must use configured exact-host Flind docs, not invented domains', () => {
    const source = read('lib/flindPublicLinks.ts')
    assert.match(source, /export function flindDocsUrl\(/)
    assert.match(source, /const docsRoot = flindPublicUrl\('docs', hostname, links\)/)
    assert.match(source, /url\.protocol !== 'https:'/)
    assert.match(source, /url\.hostname !== hostname/)
})
