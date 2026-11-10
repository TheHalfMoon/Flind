import { Region } from '~/types'

import { getUserAdminUrl } from './userAdmin'

const hosts = { [Region.US]: 'us.flind.example', [Region.EU]: 'eu.flind.example' }

describe('getUserAdminUrl first-party restrictions', () => {
    it('opens the configured target region only from another exact Flind region', () => {
        expect(getUserAdminUrl(Region.EU, 42, 'https://us.flind.example', hosts)).toBe(
            'https://eu.flind.example/admin/posthog/user/42/change/'
        )
        expect(getUserAdminUrl(Region.US, 42, 'https://eu.flind.example', hosts)).toBe(
            'https://us.flind.example/admin/posthog/user/42/change/'
        )
    })

    it.each([
        'http://localhost:8011',
        'https://us.posthog.com',
        'https://app.dev.posthog.dev',
        'https://us.flind.example.attacker.test',
        'https://us.flind.example:8443',
    ])('never redirects an unregistered origin %s to a different region', (origin) => {
        expect(getUserAdminUrl(Region.EU, 42, origin, hosts)).toBe(
            `${new URL(origin).origin}/admin/posthog/user/42/change/`
        )
    })

    it('falls back to current origin when no Flind region is configured', () => {
        expect(getUserAdminUrl(Region.EU, 42, 'https://us.posthog.com', {})).toBe(
            'https://us.posthog.com/admin/posthog/user/42/change/'
        )
        expect(getUserAdminUrl(Region.EU, 42, 'http://localhost:8011', {})).toBe(
            'http://localhost:8011/admin/posthog/user/42/change/'
        )
    })
})
