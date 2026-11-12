import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const config = readFileSync(new URL('../../products/mobile/app.config.ts', import.meta.url), 'utf8')
const eas = JSON.parse(readFileSync(new URL('../../products/mobile/eas.json', import.meta.url), 'utf8'))

test('Expo configuration cannot inherit an unrelated account, update feed or deep link', () => {
    assert.doesNotMatch(config, /4eb57b2f-79f6-4ab0-ae2c-bbd82af2cef9/)
    assert.doesNotMatch(config, /(?:slug|owner):\s*'posthog'/)
    assert.doesNotMatch(config, /\['us\.posthog\.com', 'eu\.posthog\.com'\]/)
    assert.match(config, /verifyPublishingIdentity\(\)/)
    assert.match(config, /configuredAppLinkHosts\(\)/)
    assert.match(config, /updates: \{ enabled: false \}/)
    assert.match(config, /FLIND_EXPO_OWNER/)
    assert.match(config, /FLIND_EXPO_PROJECT_ID/)
    assert.match(config, /expoProjectId \? \{ eas: \{ projectId: expoProjectId \} \}/)
})

test('store submissions and native build targets never reuse inherited identifiers', () => {
    assert.equal(eas.submit.production.ios?.ascAppId, undefined)
    assert.equal(eas.build.base.ios.scheme, undefined)
    assert.equal(eas.build.production.env.APP_VARIANT, 'production')
})

test('production icon and entitlements are not silently provisioned for an upstream Expo owner', () => {
    assert.match(config, /expoOwner\.toLowerCase\(\) === 'posthog'/)
    assert.match(config, /host\.endsWith\('\.posthog\.com'\)/)
})
