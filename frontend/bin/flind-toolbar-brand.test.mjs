import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const extensionBuilder = readFileSync(new URL('../toolbar-config.mjs', import.meta.url), 'utf8')
const extensionIcon = readFileSync(new URL('../public/icons/flind-128x128.png', import.meta.url))
const canonicalFlindLogo = readFileSync(new URL('../public/flind-icon.svg', import.meta.url), 'utf8')

test('extension selects Flind 128px icon rather than inherited vendor mascot', () => {
    const iconsBlock = extensionBuilder.match(/const TOOLBAR_EXTENSION_ICONS = \{[\s\S]*?\}/)?.[0]
    assert.ok(iconsBlock, 'browser extension icon mapping must exist')
    assert.match(iconsBlock, /128:\s*'icons\/flind-128x128\.png'/)
    assert.doesNotMatch(iconsBlock, /posthog-128x128|hedgehog/)
})

test('bundled Flind icon is a valid 128x128 PNG and comes with source vector', () => {
    assert.deepEqual(extensionIcon.subarray(0, 8), Buffer.from('89504e470d0a1a0a', 'hex'))
    assert.equal(extensionIcon.toString('ascii', 12, 16), 'IHDR')
    assert.equal(extensionIcon.readUInt32BE(16), 128, 'PNG width')
    assert.equal(extensionIcon.readUInt32BE(20), 128, 'PNG height')
    assert.match(canonicalFlindLogo, /aria-label="Flind"/)
    assert.match(canonicalFlindLogo, /#FF7259/i)
})
