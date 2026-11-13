import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import test from 'node:test'

const at = (path) => readFileSync(new URL(path, import.meta.url))
const catalog = at('../src/scenes/onboarding/sdks/allSDKs.tsx').toString('utf8')
const manifest = JSON.parse(at('../src/scenes/onboarding/shared/logos/vendor/SOURCES.json').toString('utf8'))
const vendorImports = [...catalog.matchAll(/^import (sdkVendorLogo\d+) from '\.\.\/shared\/logos\/vendor\/([^']+)'$/gm)]
const refs = [...catalog.matchAll(/\bimage:\s*(sdkVendorLogo\d+),/g)]

test('all 93 SDK catalog entries preserve owned docs and no remote image URLs', () => {
    assert.equal((catalog.match(/docsLink: flindDocsUrl\('/g) ?? []).length, 93)
    assert.equal((catalog.match(/^\s*image:\s*/gm) ?? []).length, 93)
    assert.equal(refs.length, 37)
    assert.equal(vendorImports.length, 35)
    assert.doesNotMatch(catalog, /image:\s*['"]https?:\/\//)
    assert.doesNotMatch(catalog, /res\.cloudinary\.com|dmukukwp6/)
    const names = new Set(vendorImports.map((m) => m[1]))
    assert.equal(names.size, 35)
    for (const [, name] of refs) assert.ok(names.has(name), 'missing imported SDK logo: ' + name)
})

test('all 35 local assets have exact byte, format and SHA-256 provenance, with no external SVG dependencies', () => {
    assert.equal(manifest.assets.length, 35)
    assert.equal(manifest.count, 35)
    const paths = new Set()
    for (const asset of manifest.assets) {
        assert.match(asset.url, /^https:\/\/res\.cloudinary\.com\/dmukukwp6\/image\/upload\//)
        assert.match(asset.filename, /^vendor_[a-z0-9_-]+\.(?:png|webp|svg|jpg)$/)
        assert.ok(!paths.has(asset.filename), 'duplicate local logo: ' + asset.filename)
        paths.add(asset.filename)
        const bytes = at('../src/scenes/onboarding/shared/logos/vendor/' + asset.filename)
        assert.equal(bytes.byteLength, asset.bytes, asset.filename)
        assert.equal(createHash('sha256').update(bytes).digest('hex'), asset.sha256, asset.filename)
        assert.ok(bytes.length < 1_000_001)
        if (asset.format === 'svg') {
            const svg = bytes.toString('utf8')
            assert.match(svg, /<svg(?:\s|>)/i)
            assert.doesNotMatch(svg, /<(?:script|foreignObject|iframe|object|embed)\b/i)
            assert.doesNotMatch(svg, /\son\w+\s*=/i)
            assert.doesNotMatch(svg, /(?:href|src)\s*=\s*["'](?:https?:|\/\/|javascript:)/i)
            assert.doesNotMatch(svg, /(?:url\(\s*['"]?(?:https?:|\/\/)|@import)/i)
            assert.doesNotMatch(svg, /<!DOCTYPE|<!ENTITY/i)
        } else if (asset.format === 'png') {
            assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a')
        } else if (asset.format === 'webp') {
            assert.equal(bytes.subarray(0, 4).toString('utf8'), 'RIFF')
            assert.equal(bytes.subarray(8, 12).toString('utf8'), 'WEBP')
        } else if (asset.format === 'jpg') {
            assert.equal(bytes.subarray(0, 3).toString('hex'), 'ffd8ff')
        }
    }
    assert.deepEqual(new Set(vendorImports.map((x) => x[2])), paths)
})

test('both SDK renderers consume the same locally resolved image imports without manual runtime URL loading', () => {
    const card = at('../src/scenes/onboarding/sdks/OnboardingInstallStep/SDKGrid.tsx').toString('utf8')
    const badge = at('../src/scenes/onboarding/sdks/skillBadge.tsx').toString('utf8')
    assert.match(card, /<img src=\{sdk\.image\}/)
    assert.match(badge, /<img src=\{image\}/)
    assert.match(catalog, /SDK logos are bundled with Flind/)
})
