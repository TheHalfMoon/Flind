import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const location = new URL('../src/lib/components/Errors/Exception/known-exceptions/javascript/', import.meta.url)
const read = (name) => readFileSync(new URL(name + '.tsx', location), 'utf8')
const files = {
    promise: read('non-error-promise-rejection'),
    react: read('react-minified-error'),
    script: read('script-error'),
    syntax: read('syntax-error'),
}

test('all four live Flind exception banners provide guidance without donor documentation links', () => {
    for (const [name, content] of Object.entries(files)) {
        assert.doesNotMatch(content, /posthog\.com|<Link\b[^>]*to="https:\/\/posthog\.com/i, name)
        assert.match(content, /defineKnownException\(/)
        assert.match(content, /<KnownExceptionBanner>/)
    }
})

test('promise rejection banner explains that Error instances preserve stack context', () => {
    assert.match(files.promise, /exception\.value\?\.startsWith\('Non-Error promise rejection'\)/)
    assert.match(files.promise, /Promise\.reject\(new Error\(message\)\)/)
    assert.doesNotMatch(files.promise, /import \{ Link \}/)
})

test('React production error decoder uses the numeric capture group, not the whole regex match array', () => {
    assert.match(files.react, /extractReactErrorCode\(exception\.value\)/)
    assert.match(files.react, /https:\/\/react\.dev\/errors\//)
    assert.match(files.react, /errorCode && \(/)
    assert.doesNotMatch(files.react, /to=\{\x60https:\/\/react\.dev\/errors\/\$\{errorCode\}\x60\}/)
})

test('Script error guidance recommends cross-origin diagnostics without inherited docs links', () => {
    assert.match(files.script, /exception\.value\.startsWith\('Script error'\)/)
    assert.match(files.script, /crossorigin="anonymous"/)
    assert.match(files.script, /CORS/)
    assert.doesNotMatch(files.script, /import \{ Link \}/)
})

test('SyntaxError guidance correctly distinguishes parse errors from cross-origin restrictions', () => {
    assert.match(files.syntax, /exception\.type === 'SyntaxError'/)
    assert.match(files.syntax, /JavaScript failed to parse code/)
    assert.match(files.syntax, /source maps/)
    assert.doesNotMatch(files.syntax, /cross-origin restrictions|import \{ Link \}/)
})
