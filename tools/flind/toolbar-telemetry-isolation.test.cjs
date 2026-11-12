const assert = require('node:assert/strict')
const { test } = require('node:test')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { readFileSync, existsSync } = require('node:fs')
const { chromium } = require('playwright-core')
const esbuild = require('esbuild')

const sourceFile = process.env.FLIND_TOOLBAR_SOURCE
assert.ok(sourceFile, 'Set FLIND_TOOLBAR_SOURCE to toolbarPosthogJS.ts from the checkout.')
const source = readFileSync(sourceFile, 'utf8')
assert.doesNotMatch(source, /internal-cf\.posthog\.com|sTMFPsFhdP1Ssg/, 'No inherited hosted telemetry key/URL')
assert.match(source, /before_send: telemetryDisabled \? \(\) => null : undefined/)
assert.match(source, /advanced_disable_decide: telemetryDisabled/)
assert.match(source, /advanced_disable_feature_flags: telemetryDisabled/)
assert.match(source, /runningOnFlind = !!window\.POSTHOG_APP_CONTEXT && !!window\.JS_POSTHOG_API_KEY/)

const browserPath = process.env.FLIND_HEADLESS_BROWSER || [
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/opt/google/chrome/chrome',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
].find(existsSync)
const ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/123.0.0.0 Safari/537.36'
const fakeToken = 'phc_flind_synthetic_local_only'

test('actual Flind toolbar module never contacts inherited hosted telemetry outside the Flind app', { timeout: 60000 }, async () => {
    assert.ok(browserPath, 'No Chrome/Edge binary available')
    const built = await esbuild.build({
        stdin: {
            contents: source + '\nwindow.__flindToolbar = toolbarPosthogJS;\n',
            resolveDir: process.cwd(),
            sourcefile: 'toolbarPosthogJS.ts',
            loader: 'ts',
        },
        bundle: true,
        platform: 'browser',
        format: 'iife',
        write: false,
        logLevel: 'silent',
    })
    const toolbarScript = built.outputFiles[0].contents
    const received = []
    const server = createServer(async (req, res) => {
        const path = new URL(req.url, 'http://127.0.0.1').pathname
        if (path === '/toolbar.js') {
            res.writeHead(200, { 'Content-Type': 'application/javascript' })
            return res.end(toolbarScript)
        }
        if (req.method === 'POST') {
            received.push({method: req.method, path})
            for await (const _chunk of req) {}
            res.writeHead(200, { 'Content-Type': 'application/json' })
            return res.end('{"status":1}')
        }
        if (path !== '/' && path !== '/favicon.ico') received.push({method: req.method, path})
        res.writeHead(200, { 'Content-Type': path === '/' ? 'text/html' : 'application/json' })
        res.end(path === '/' ? '<!doctype html><script src="/toolbar.js"></script>' : '{}')
    })
    server.listen(0, '127.0.0.1')
    await once(server, 'listening')
    const origin = `http://127.0.0.1:${server.address().port}`
    let browser
    try {
        browser = await chromium.launch({ executablePath: browserPath, headless: true, args: ['--no-sandbox'] })
        for (const isFlindApp of [false, true]) {
            received.length = 0
            const context = await browser.newContext({ userAgent: ua, serviceWorkers: 'block' })
            try {
                const page = await context.newPage()
                const externalOrigins = []
                await page.route('**/*', route => {
                    const candidate = new URL(route.request().url())
                    if (candidate.origin !== origin) {
                        externalOrigins.push(candidate.origin)
                        return route.abort()
                    }
                    return route.continue()
                })
                await page.addInitScript(({ app, token }) => {
                    if (app) {
                        window.POSTHOG_APP_CONTEXT = {}
                        window.JS_POSTHOG_API_KEY = token
                        window.JS_POSTHOG_HOST = location.origin
                    } else {
                        // Deliberately provide the inherited host without a Flind app context.
                        // The toolbar must ignore it rather than making a donor-hosted request.
                        window.JS_POSTHOG_HOST = 'https://internal-cf.posthog.com'
                        window.JS_POSTHOG_API_KEY = undefined
                        window.POSTHOG_APP_CONTEXT = undefined
                    }
                }, { app: isFlindApp, token: fakeToken })
                await page.goto(origin + '/')
                await page.waitForFunction(() => !!window.__flindToolbar, null, { timeout: 12000 })
                const state = await page.evaluate(() => {
                    const sdk = window.__flindToolbar
                    sdk.set_config({ opt_out_useragent_filter: true })
                    sdk.opt_in_capturing()
                    sdk.capture('flind_synthetic_toolbar', { synthetic_only: true })
                    sdk.identify('flind_synthetic_identity')
                    sdk.reloadFeatureFlags()
                    return {
                        host: sdk.config.api_host,
                        filterInstalled: typeof sdk.config.before_send === 'function',
                        flagsDisabled: sdk.config.advanced_disable_feature_flags === true,
                        decideDisabled: sdk.config.advanced_disable_decide === true,
                    }
                })
                assert.equal(state.host, origin)
                if (!isFlindApp) {
                    assert.equal(state.filterInstalled, true, 'customer pages must drop all SDK capture events')
                    assert.equal(state.flagsDisabled, true, 'customer pages must disable feature flag requests')
                    assert.equal(state.decideDisabled, true, 'customer pages must disable decide requests')
                } else {
                    assert.equal(state.flagsDisabled, false, 'local Flind app should retain flag functionality')
                }
                for (let i = 0; i < 15; i++) {
                    if (isFlindApp && received.some(r => r.method === 'POST' && r.path === '/e/')) break
                    await page.waitForTimeout(200)
                }
                assert.deepEqual(externalOrigins, [], 'SDK tried an off-instance network origin')
                if (isFlindApp) {
                    assert.ok(received.some(r => r.method === 'POST' && r.path === '/e/'), 'Flind app did not send its synthetic event locally')
                } else {
                    assert.deepEqual(received, [], 'customer page/extension SDK attempted local telemetry or flags')
                }
                console.log(`Flind toolbar telemetry: appContext=${isFlindApp}, localRequests=${received.length}, offInstance=0`)
            } finally {
                await context.close()
            }
        }
    } finally {
        if (browser) await browser.close()
        server.closeAllConnections()
        await new Promise(resolve => server.close(resolve))
    }
})
