import { describe, expect, it } from 'vitest'

import worker from '@/index'
import REGION_PICKER_HTML from '../src/static/region-picker.html'

describe('Flind first-party OAuth region picker', () => {
    it('renders the Flind name without an inherited vendor identity or external links', () => {
        expect(REGION_PICKER_HTML).toContain('<title>Authenticate with Flind</title>')
        expect(REGION_PICKER_HTML).toContain('Authenticate with Flind')
        expect(REGION_PICKER_HTML).toContain('Select Flind region')
        expect(REGION_PICKER_HTML).toContain('US region')
        expect(REGION_PICKER_HTML).toContain('EU region')
        expect(REGION_PICKER_HTML).not.toMatch(/posthog\.com|PostHog|@posthog\/brand/i)
    })

    it('has no external font requests or obsolete bundled font dependencies', () => {
        expect(REGION_PICKER_HTML).not.toMatch(/\/static\/fonts\/|@font-face|rel="preload"[^>]*font/i)
        expect(REGION_PICKER_HTML).toContain('-apple-system')
    })

    it('does not serve an unused font route when OAuth regions are unconfigured', async () => {
        const response = await worker.fetch(
            new Request('https://oauth.flind.example/static/fonts/unused.woff2'),
            { AUTH_KV: {} as KVNamespace }
        )
        expect(response.status).toBe(404)
    })
})
