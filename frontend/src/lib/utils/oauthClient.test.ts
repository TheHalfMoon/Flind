import {
    buildAuthorizeUrl,
    configuredOAuthRegion,
    getBackendHost,
    getRegionForHost,
    getStoredSession,
    isApprovedOAuthTarget,
    OAUTH_REGIONS,
} from './oauthClient'

import { Region } from '~/types'

describe('Flind OAuth first-party isolation', () => {
    const originalUS = { ...OAUTH_REGIONS[Region.US] }
    const originalEU = { ...OAUTH_REGIONS[Region.EU] }

    beforeEach(() => {
        OAUTH_REGIONS[Region.US].host = ''
        OAUTH_REGIONS[Region.US].clientId = ''
        OAUTH_REGIONS[Region.EU].host = ''
        OAUTH_REGIONS[Region.EU].clientId = ''
        window.localStorage.clear()
    })

    afterEach(() => {
        Object.assign(OAUTH_REGIONS[Region.US], originalUS)
        Object.assign(OAUTH_REGIONS[Region.EU], originalEU)
        window.localStorage.clear()
    })

    test('no external OAuth host or bearer session when unconfigured', async () => {
        expect(configuredOAuthRegion(Region.US)).toBeNull()
        expect(getRegionForHost('')).toBeNull()
        expect(isApprovedOAuthTarget('https://untrusted.example', 'id')).toBe(false)
        expect(getBackendHost()).toBeNull()
        await expect(
            buildAuthorizeUrl({
                backendHost: 'https://untrusted.example',
                clientId: 'untrusted-client',
                codeVerifier: 'verifier',
                state: 'state',
                returnTo: '/',
            })
        ).rejects.toThrow('Flind OAuth is not configured')
    })

    test('a stored legacy or unregistered host cannot activate OAuth', () => {
        window.localStorage.setItem(
            'flind_oauth_session',
            JSON.stringify({
                backendHost: 'https://untrusted.example',
                clientId: 'untrusted-client',
                accessToken: 'secret',
                refreshToken: 'refresh',
                expiresAt: 9999999999999,
            })
        )
        expect(getStoredSession()).toBeNull()
        expect(getBackendHost()).toBeNull()
    })

    test('only a configured first-party Flind region and matching client are usable', () => {
        OAUTH_REGIONS[Region.US].host = 'https://us.flind.example'
        OAUTH_REGIONS[Region.US].clientId = 'registered-flind-client'
        expect(configuredOAuthRegion(Region.US)?.host).toBe('https://us.flind.example')
        expect(isApprovedOAuthTarget('https://us.flind.example', 'registered-flind-client')).toBe(true)
        expect(isApprovedOAuthTarget('https://us.flind.example.evil.example', 'registered-flind-client')).toBe(false)
        expect(isApprovedOAuthTarget('https://us.flind.example', 'wrong-client')).toBe(false)
        expect(getRegionForHost('https://us.flind.example')).toBe(Region.US)

        window.localStorage.setItem(
            'flind_oauth_session',
            JSON.stringify({
                backendHost: 'https://us.flind.example',
                clientId: 'registered-flind-client',
                accessToken: 'oauth-token',
                refreshToken: 'refresh',
                expiresAt: 9999999999999,
            })
        )
        expect(getStoredSession()?.accessToken).toBe('oauth-token')
        expect(getBackendHost()).toBe('https://us.flind.example')
    })

    test('ports, paths, embedded userinfo and insecure hosts cannot be configured', () => {
        OAUTH_REGIONS[Region.EU].clientId = 'registered-flind-client'
        for (const host of [
            'http://eu.flind.example',
            'https://eu.flind.example:8443',
            'https://user@eu.flind.example',
            'https://eu.flind.example/path',
        ]) {
            OAUTH_REGIONS[Region.EU].host = host
            expect(configuredOAuthRegion(Region.EU)).toBeNull()
        }
    })
})
