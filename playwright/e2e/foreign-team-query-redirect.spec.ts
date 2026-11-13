import { expect, test, type APIRequestContext } from '@playwright/test'
import { assertForeignPersonalKeyCannotQueryTeam } from '../utils/assert-foreign-team-query-denied'

/**
 * No network or credentials: simulate the HTTP response from the exact
 * target endpoint and ensure redirects cannot masquerade as denials.
 */
for (const status of [301, 302, 303, 307, 308, 200, 500]) {
    test(`foreign-key probe rejects HTTP ${status} rather than treating it as authorization denial`, async () => {
        let observedOptions: Record<string, unknown> | undefined
        const request = {
            post: async (_url: string, options: Record<string, unknown>) => {
                observedOptions = options
                return { status: () => status }
            },
        } as unknown as APIRequestContext

        await expect(
            assertForeignPersonalKeyCannotQueryTeam(request, '42', 'synthetic_foreign_key', 'synthetic_event')
        ).rejects.toThrow()
        expect(observedOptions?.maxRedirects).toBe(0)
        expect(observedOptions?.headers).toEqual({ Authorization: 'Bearer synthetic_foreign_key' })
    })
}

for (const status of [401, 403, 404]) {
    test(`foreign-key probe accepts direct HTTP ${status} denial`, async () => {
        const request = {
            post: async (_url: string, options: Record<string, unknown>) => {
                expect(options.maxRedirects).toBe(0)
                return { status: () => status }
            },
        } as unknown as APIRequestContext
        await assertForeignPersonalKeyCannotQueryTeam(request, '42', 'synthetic_foreign_key', 'synthetic_event')
    })
}
