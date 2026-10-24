import { BOT_NAME, flindImageBotIdentityOrigin, REQUEST_IDENTITY_HEADERS } from './flind-image-bot-identity'

describe('Flind image bot identity', () => {
    it('does not claim inherited product identity by default', () => {
        expect(BOT_NAME).toBe('FlindImageFetcherBot')
        expect(REQUEST_IDENTITY_HEADERS['user-agent']).toBe('FlindImageFetcherBot/1.0')
    })

    it('requires explicit HTTPS origin before accepting a public bot identity', () => {
        expect(flindImageBotIdentityOrigin('')).toBeNull()
        expect(flindImageBotIdentityOrigin('https://identity.flind.example')).toBe('https://identity.flind.example')
    })

    it.each([
        'https://us.posthog.com',
        'https://posthog.com.',
        'http://flind.example',
        'https://person:secret@flind.example',
        'https://flind.example/other',
        'https://flind.example?token=value',
        ' https://flind.example',
    ])('rejects unsafe or inherited identity origins: %s', (host) => {
        expect(() => flindImageBotIdentityOrigin(host)).toThrow()
    })
})
