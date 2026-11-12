import assert from 'node:assert/strict'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL('../../' + path, import.meta.url), 'utf8')
const candidate = 'com.thehalfmoon.flind.mobile'
const config = JSON.parse(read('products/mobile/src/lib/appVariants.json'))

test('native bundles, app display names and callback schemes use the independent Flind identity', () => {
    assert.equal(config.productionAppIds.ios, candidate)
    assert.equal(config.productionAppIds.android, candidate)
    assert.deepEqual(
        Object.entries(config.variants).map(([variant, value]) => [variant, value.name, value.scheme]),
        [
            ['development', 'Flind Dev', 'flind-dev'],
            ['preview', 'Flind Preview', 'flind-preview'],
            ['production', 'Flind', 'flind'],
        ]
    )
    assert.match(read('products/mobile/app/+native-intent.tsx'), /flind\(\?:-dev\|-preview\)/)
    assert.match(read('products/mobile/shared/handoffProtocol.ts'), /'flind-dev:'/)
    assert.match(read('products/mobile/shared/handoffProtocol.ts'), /'flind-preview:'/)
    assert.doesNotMatch(read('products/mobile/shared/handoffProtocol.ts'), /posthog-(?:dev|preview):/)
})

test('backend app-link and OAuth registration matches all Flind native variants', () => {
    const links = read('posthog/mobile_app_links.py')
    const oauth = read('products/tasks/backend/management/commands/setup_tasks_oauth.py')
    const variants = Object.values(config.variants)
    for (const variant of variants) {
        const id = candidate + variant.idSuffix
        assert.ok(links.includes('"' + id + '"'), 'Missing app-link bundle: ' + id)
        assert.ok(oauth.includes('"' + variant.scheme + '://callback') ||
            oauth.includes(' ' + variant.scheme + '://callback'), 'Missing OAuth callback: ' + variant.scheme)
    }
    assert.doesNotMatch(links, /com\.posthog\.(?:code\.)?mobile/)
    assert.doesNotMatch(oauth, /posthog(?:-dev|-preview)?:\/\/callback/)
})

test('Kotlin packages and Expo module registries move together without legacy package paths', () => {
    const dirs = [
        ['chart-widget', 'chart', 12],
        ['hedgehog-widget', 'hedgehog', 5],
        ['notification-intents', 'notifications', 3],
    ]
    for (const [module, pkg, count] of dirs) {
        const path = module === 'notification-intents'
            ? 'products/mobile/modules/' + module + '/android/src/main/java/com/thehalfmoon/flind/mobile/' + pkg
            : 'products/mobile/modules/' + module + '/android/src/main/java/com/thehalfmoon/flind/mobile/' + pkg
        assert.equal(readdirSync(new URL('../../' + path, import.meta.url)).filter((n) => n.endsWith('.kt')).length, count, module)
        const old = module === 'notification-intents'
            ? 'products/mobile/modules/' + module + '/android/src/main/java/com/posthog/mobile/' + pkg
            : 'products/mobile/modules/' + module + '/android/src/main/java/com/posthog/code/mobile/' + pkg
        assert.equal(existsSync(new URL('../../' + old, import.meta.url)), false, old)
        const registry = read('products/mobile/modules/' + module + '/expo-module.config.json')
        assert.ok(registry.includes('com.thehalfmoon.flind.mobile.' + pkg), module)
        assert.doesNotMatch(registry, /com\.posthog\./)
    }
    const chartTest = 'products/mobile/modules/chart-widget/android/src/test/java/com/thehalfmoon/flind/mobile/chart/ChartWidgetRefreshTest.kt'
    assert.equal(existsSync(new URL('../../' + chartTest, import.meta.url)), true)
})

test('mobile identity is still release-blocked until Flind registration and native tests exist', () => {
    const docs = read('products/mobile/docs/FLIND_NATIVE_IDENTITIES.md')
    assert.match(docs, /NO-GO/)
    assert.match(docs, /not registered/)
    const expo = read('products/mobile/app.config.ts')
    assert.match(expo, /updates: \{ enabled: false \}/)
})
