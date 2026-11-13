import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/scenes/onboarding/sdks/sdk-install-instructions/react-native.tsx', import.meta.url), 'utf8')

test('React Native setup never navigates to or advertises inherited donor docs', () => {
    assert.doesNotMatch(source, /https?:\/\/(?:app\.)?posthog\.com\b/i)
    assert.match(source, /import \{ flindDocsSectionUrl \} from 'lib\/flindPublicLinks'/)
    assert.match(source, /flindDocsSectionUrl\('libraries\/react-native', 'without-the-posthogprovider'\)/)
    assert.match(source, /\{directSetupDocs \? \(/)
    assert.match(source, /<Link to=\{directSetupDocs\}>read the Flind setup documentation<\/Link>/)
    assert.match(source, /consult the React Native configuration guidance for your Flind instance/)
})

test('Native SDK setup retains project-owned host, team token placeholder and provider API', () => {
    assert.match(source, /import \{ apiHostOrigin \} from 'lib\/utils\/apiHost'/)
    assert.match(source, /const url = apiHostOrigin\(\)/)
    assert.match(source, /currentTeam\?\.api_token \?\? 'YOUR_PROJECT_API_KEY'/)
    assert.match(source, /import \{ PostHogProvider \} from 'posthog-react-native'/)
    assert.match(source, /enableSessionReplay: true/)
})

test('Privacy controls and opt-in replay/surveys remain unchanged', () => {
    for (const term of [
        'includeReplay', 'includeSurveys', 'maskAllTextInputs: true',
        'maskAllImages: true', 'captureNetworkTelemetry: false',
        'captureLog: false', 'throttleDelayMs: 1000', 'PostHogSurveyProvider',
    ]) {
        assert.ok(source.includes(term), term)
    }
})
