import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL('../../' + path, import.meta.url), 'utf8')

test('mobile status checks require Flind-owned explicit HTTPS configuration', () => {
    const src = read('products/mobile/src/features/status/usePostHogStatus.ts')
    assert.doesNotMatch(src, /const STATUS_PAGE = 'https:\/\/www\.posthogstatus\.com'/)
    assert.match(src, /EXPO_PUBLIC_FLIND_STATUS_URL/)
    assert.match(src, /posthogstatus\.com/)
    assert.match(src, /flindStatusOrigin/)
    assert.match(src, /enabled: Boolean\(statusOrigin\) && region !== 'custom'/)
    assert.match(src, /credentials: 'omit'/)
    assert.match(src, /redirect: 'error'/)
})
test('mobile menu cannot open or advertise an unconfigured donor status page', () => {
    const menu = read('products/mobile/src/features/tabs/NavMenu.tsx')
    const tabs = read('products/mobile/src/features/tabs/TabsChrome.tsx')
    assert.match(menu, /\{statusPageUrl \? \(/)
    assert.match(tabs, /if \(status\.pageUrl\)/)
    assert.doesNotMatch(tabs, /posthogstatus\.com/)
})
