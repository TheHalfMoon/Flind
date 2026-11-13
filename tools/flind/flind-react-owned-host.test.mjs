import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const root = resolve(fileURLToPath(new URL('../../', import.meta.url)))
const { flindReactOwnedOrigin, flindReactOwnedOptions } =
    await import('../../packages/react/src/context/flindOwnedHost.ts')

test('Flind React SDK rejects missing and inherited analytics origins without fallback', () => {
    for (const host of [
        undefined, '', 'not-a-url',
        'http://collector.flind.example',
        'http://localhost:9000',
        'https://us.i.posthog.com',
        'https://app.posthog.com',
        'https://eu.posthog.com',
        'https://posthog.dev',
        'https://posthogstatus.com',
        'https://posthog.com...',
        'https://user:secret@collector.flind.example',
        'https://collector.flind.example/extra',
        'https://collector.flind.example/?token=synthetic',
        'https://collector.flind.example/#anchor',
    ]) {
        assert.equal(flindReactOwnedOrigin(host), null, String(host))
        assert.equal(flindReactOwnedOptions(host === undefined ? undefined : { api_host: host }), null, String(host))
    }
})

test('Flind React SDK derives UI host only from validated independent collector', () => {
    assert.deepEqual(
        flindReactOwnedOptions({ api_host: 'https://collector.flind.example/', capture_pageview: false }),
        { api_host: 'https://collector.flind.example', ui_host: 'https://collector.flind.example', capture_pageview: false }
    )
    assert.deepEqual(
        flindReactOwnedOptions({
            api_host: 'https://collector.flind.example',
            ui_host: 'https://analytics-ui.flind.example',
        }),
        { api_host: 'https://collector.flind.example', ui_host: 'https://analytics-ui.flind.example' }
    )
    assert.equal(
        flindReactOwnedOptions({ api_host: 'https://collector.flind.example', ui_host: 'https://us.posthog.com' }),
        null
    )
    assert.equal(flindReactOwnedOrigin('http://127.0.0.1:9000'), 'http://127.0.0.1:9000')
})

test('source and checked-in full ESM/UMD React packages enforce identical default-deny boundary', () => {
    for (const path of [
        'packages/react/src/context/PostHogProvider.tsx',
        'packages/react/dist/esm/index.js',
        'packages/react/dist/umd/index.js',
    ]) {
        const code = readFileSync(resolve(root, path), 'utf8')
        assert.match(code, /flindReactOwnedOptions\(options\)/)
        assert.match(code, /analytics disabled/)
        assert.match(code, /opt_out_capturing\(\)/)
        assert.match(code, /\.init\(apiKey, safeOptions\)/)
        assert.match(code, /\.set_config\(safeOptions\)/)
        assert.doesNotMatch(code, /\.init\(apiKey, options\)/)
        assert.doesNotMatch(code, /\.set_config\(options\)/)
    }
})
