import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import test from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const require = createRequire(import.meta.url)
const donor = require('@posthog/react')
const flind = require('@flind/react')

test('Flind React compatibility package preserves the published entrypoint API', () => {
    assert.deepEqual(Object.keys(flind).sort(), Object.keys(donor).sort())
    assert.equal(typeof flind.PostHogErrorBoundary, 'function')
    assert.equal(typeof flind.usePostHog, 'function')
})

test('Flind React consumer reads the same context as existing provider', () => {
    const client = { config: {}, captureException: () => 'event-1' }
    let observed
    function Reader() {
        observed = flind.usePostHog()
        return React.createElement('span', null, 'Flind')
    }
    const html = renderToStaticMarkup(
        React.createElement(donor.PostHogProvider, { client }, React.createElement(Reader))
    )
    assert.equal(html, '<span>Flind</span>')
    assert.equal(observed, client, 'No second React analytics context must be introduced')
})

test('Flind React slim and survey entrypoints preserve upstream exports', () => {
    for (const subpath of ['/slim', '/surveys']) {
        assert.deepEqual(
            Object.keys(require('@flind/react' + subpath)).sort(),
            Object.keys(require('@posthog/react' + subpath)).sort(),
            'Incompatible API at ' + subpath
        )
    }
})
