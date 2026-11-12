const assert = require('node:assert/strict')
const { test } = require('node:test')
const { chromium } = require('playwright-core')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { existsSync, readFileSync } = require('node:fs')
const { join, dirname } = require('node:path')

const installedSDK = require('posthog-js/package.json')
assert.equal(installedSDK.version, '1.447.1', 'the smoke must exercise Flind\'s pinned browser SDK release')
const sdkBundle = readFileSync(join(dirname(require.resolve('posthog-js/package.json')), 'dist/array.js'))
const browserPath = process.env.FLIND_HEADLESS_BROWSER || [
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/opt/google/chrome/chrome',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
].find(existsSync)
const syntheticUA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/123.0.0.0 Safari/537.36'

test('headless browser SDK sends a local capture only when the synthetic bot filter is disabled', { timeout: 60000 }, async () => {
    assert.ok(browserPath && existsSync(browserPath), 'Chrome/Edge missing; set FLIND_HEADLESS_BROWSER')
    const received = []
    let unexpectedPortRequests = 0
    const forbiddenServer = createServer((_req, res) => {
        unexpectedPortRequests++
        res.writeHead(200, { 'Content-Type': 'text/plain' })
        res.end('must not be reached')
    })
    const server = createServer(async (req, res) => {
        const path = new URL(req.url, 'http://127.0.0.1').pathname
        if (path === '/static/array.js') {
            res.writeHead(200, { 'Content-Type': 'application/javascript' })
            return res.end(sdkBundle)
        }
        if (req.method === 'POST') {
            received.push(path)
            for await (const _ of req) {}
            res.writeHead(200, { 'Content-Type': 'application/json' })
            return res.end('{"status":1}')
        }
        if (path === '/') {
            res.writeHead(200, { 'Content-Type': 'text/html' })
            return res.end(`<!doctype html><script src="/static/array.js"></script><script>
                window.__flind_ready = false;
                posthog.init('phc_flind_synthetic_local', {
                    api_host: location.origin, autocapture: false, capture_pageview: false,
                    capture_pageleave: false, disable_session_recording: true,
                    advanced_disable_decide: true, request_batching: false,
                    disable_persistence: true, opt_out_useragent_filter: window.__allow_synthetic_bot,
                    loaded: function() { window.__flind_ready = true }
                });
            </script>`)
        }
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end('{}')
    })
    server.listen(0, '127.0.0.1')
    await once(server, 'listening')
    forbiddenServer.listen(0, '127.0.0.1')
    await once(forbiddenServer, 'listening')
    const origin = `http://127.0.0.1:${server.address().port}`
    const forbiddenOrigin = `http://127.0.0.1:${forbiddenServer.address().port}`
    assert.notEqual(origin, forbiddenOrigin)
    let browser
    try {
        browser = await chromium.launch({ executablePath: browserPath, headless: true, args: ['--no-sandbox'] })
        for (const allowBot of [false, true]) {
            received.length = 0
            const context = await browser.newContext({ userAgent: syntheticUA, serviceWorkers: 'block' })
            try {
                const page = await context.newPage()
                const blocked = []
                await page.route('**/*', route => {
                    if (new URL(route.request().url()).origin !== origin) {
                        blocked.push(new URL(route.request().url()).origin)
                        return route.abort()
                    }
                    return route.continue()
                })
                await page.addInitScript(value => { window.__allow_synthetic_bot = value }, allowBot)
                await page.goto(origin + '/')
                await page.waitForFunction(() => window.__flind_ready === true, null, { timeout: 12000 })
                const result = await page.evaluate(() => {
                    const sdk = window.posthog
                    return {
                        loaded: sdk.__loaded === true,
                        bot: sdk._is_bot(),
                        capturing: sdk.is_capturing(),
                        apiHostLocal: sdk.config.api_host === location.origin,
                        accepted: sdk.capture('flind_synthetic_browser', { test_only: true }) !== undefined,
                    }
                })
                assert.deepEqual(result, {
                    loaded: true, bot: true, capturing: true, apiHostLocal: true, accepted: allowBot,
                })
                for (let i = 0; i < (allowBot ? 20 : 4); i++) {
                    if (allowBot && received.includes('/e/')) break
                    await page.waitForTimeout(200)
                }
                assert.deepEqual(blocked, [], 'browser SDK attempted a request outside its exact instance origin')
                if (allowBot) {
                    assert.ok(received.includes('/e/'), 'SDK accepted capture but sent no local /e/ event')
                } else {
                    assert.deepEqual(received, [], 'SDK ignored bot filter and emitted a request')
                }
                // Negative control: a different port on the same loopback IP MUST be
                // blocked at routing, not merely fail due to CORS after reaching it.
                const probe = await page.evaluate(url => fetch(url).then(() => 'permitted', () => 'blocked'), forbiddenOrigin + '/probe')
                assert.equal(probe, 'blocked')
                assert.deepEqual(blocked, [forbiddenOrigin], 'the exact-origin route guard did not reject the other local port')
                assert.equal(unexpectedPortRequests, 0, 'a forbidden same-host different-port request reached the server')
                console.log(`Headless SDK test: allowBot=${allowBot}, accepted=${result.accepted}, localPosts=${received.length}, forbiddenPortBlocked=true`)
            } finally {
                await context.close()
            }
        }
    } finally {
        if (browser) await browser.close()
        server.closeAllConnections()
        forbiddenServer.closeAllConnections()
        await Promise.all([
            new Promise(resolve => server.close(resolve)),
            new Promise(resolve => forbiddenServer.close(resolve)),
        ])
    }
})
