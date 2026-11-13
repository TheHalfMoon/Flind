import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const root = new URL('../src/scenes/onboarding/sdks/sdk-install-instructions/', import.meta.url)
const source = (filename) => readFileSync(new URL(filename, root), 'utf8')
const files = ['flutter.tsx', 'nuxt.tsx', 'vue.tsx', 'android.tsx', 'ios.tsx']
const sources = Object.fromEntries(files.map((filename) => [filename, source(filename)]))
const flindPublicLinks = readFileSync(new URL('../src/lib/flindPublicLinks.ts', import.meta.url), 'utf8')

test('all five SDK framework install guide sources are free of inherited provider documentation URLs', () => {
    for (const [filename, content] of Object.entries(sources)) {
        assert.doesNotMatch(content, /posthog\.com\/docs|github\.com\/PostHog\/posthog-js\/wiki/i, filename)
        assert.doesNotMatch(content, /<Link\s+to="https:\/\/posthog\.com\//, filename)
    }
})

test('Nuxt and Vue SDK onboarding show owned links only when explicitly configured', () => {
    const nuxt = sources['nuxt.tsx']
    const vue = sources['vue.tsx']
    assert.match(nuxt, /flindDocsSectionUrl\('libraries\/nuxt-js', 'nuxt-v216-and-below'\)/)
    assert.match(nuxt, /legacyNuxtDocs \? \(/)
    assert.match(nuxt, /<Link to=\{legacyNuxtDocs\}>Flind Nuxt docs<\/Link>/)
    assert.match(nuxt, /Flind Nuxt documentation when configured/)
    assert.match(vue, /flindDocsUrl\('libraries\/vue-js'\)/)
    assert.match(vue, /legacyVueDocs \? \(/)
    assert.match(vue, /<Link to=\{legacyVueDocs\}>Flind Vue docs<\/Link>/)
    assert.match(vue, /Flind Vue documentation when configured/)
})

test('Flutter tutorial shows first-party link only when available and keeps a readable fallback', () => {
    const flutter = sources['flutter.tsx']
    assert.match(flutter, /flindDocsSectionUrl\('libraries\/flutter', 'example'\)/)
    assert.match(flutter, /flutterObserverDocs \? \(/)
    assert.match(flutter, /<Link to=\{flutterObserverDocs\}>PosthogObserver<\/Link>/)
    assert.match(flutter, /<code>PosthogObserver<\/code>/)
    assert.match(flutter, /config\.sessionReplayConfig\.maskAllImages = false/)
    assert.match(flutter, /Posthog\(\)\.screen/)
})

test('mobile session replay configuration snippets remain usable without sending developers to vendor docs', () => {
    const android = sources['android.tsx']
    const ios = sources['ios.tsx']
    assert.match(android, /config\.sessionReplay = true/)
    assert.match(ios, /config\.sessionReplay = true/)
    assert.match(android, /Flind Android session replay guide when configured/)
    assert.match(ios, /Flind iOS session replay guide when configured/)
    assert.match(flindPublicLinks, /export function flindDocsSectionUrl\(/)
    assert.match(flindPublicLinks, /const docsUrl = flindDocsUrl\(relativePath, hostname, links\)/)
})
