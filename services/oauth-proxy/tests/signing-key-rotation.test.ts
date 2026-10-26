import { exportPKCS8, generateKeyPair } from 'jose'
import { describe, expect, it } from 'vitest'

import { proxyJwks } from '@/lib/idtoken'

async function newFlindKey(): Promise<string> {
    const { privateKey } = await generateKeyPair('RS256', { extractable: true })
    return exportPKCS8(privateKey)
}

describe('Flind OIDC signing key rotation inside one worker isolate', () => {
    it('uses a new kid when the active PEM is rotated without restarting the worker', async () => {
        const firstPem = await newFlindKey()
        const secondPem = await newFlindKey()

        const first = await proxyJwks({ OIDC_SIGNING_KEY: firstPem })
        const second = await proxyJwks({ OIDC_SIGNING_KEY: secondPem })
        expect(first).toHaveLength(1)
        expect(second).toHaveLength(1)
        expect(second[0]?.kid).not.toBe(first[0]?.kid)
        expect(second[0]?.n).not.toBe(first[0]?.n)

        const previous = await proxyJwks({ OIDC_SIGNING_KEY: firstPem })
        expect(previous[0]?.kid).toBe(first[0]?.kid)
    })

    it('publishes newly configured inactive rotation key, not a stale inactive slot', async () => {
        const active = await newFlindKey()
        const inactiveA = await newFlindKey()
        const inactiveB = await newFlindKey()

        const initial = await proxyJwks({ OIDC_SIGNING_KEY: active, OIDC_SIGNING_KEY_INACTIVE_1: inactiveA })
        const rotated = await proxyJwks({ OIDC_SIGNING_KEY: active, OIDC_SIGNING_KEY_INACTIVE_1: inactiveB })
        expect(initial).toHaveLength(2)
        expect(rotated).toHaveLength(2)
        expect(rotated[0]?.kid).toBe(initial[0]?.kid)
        expect(rotated[1]?.kid).not.toBe(initial[1]?.kid)
    })

    it('normalizes escaped newlines and never publishes a key when none is configured', async () => {
        const active = await newFlindKey()
        const escaped = active.replaceAll('\n', '\\n')
        const normal = await proxyJwks({ OIDC_SIGNING_KEY: active })
        const fromEscaped = await proxyJwks({ OIDC_SIGNING_KEY: escaped })
        expect(normal[0]?.kid).toBe(fromEscaped[0]?.kid)
        expect(await proxyJwks({})).toEqual([])
    })
})
