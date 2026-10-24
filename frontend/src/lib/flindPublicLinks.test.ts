import { flindPublicUrl } from './flindPublicLinks'

describe('Flind public help links', () => {
    const ownedHost = 'www.flind.example'
    const docs = { docs: 'https://www.flind.example/docs' }

    it('does not assume a documentation or community domain exists', () => {
        expect(flindPublicUrl('docs', '', docs)).toBeNull()
        expect(flindPublicUrl('community', ownedHost, {})).toBeNull()
        expect(flindPublicUrl('changelog', ownedHost, {})).toBeNull()
    })

    it('accepts exact first-party HTTPS URLs when configured', () => {
        expect(flindPublicUrl('docs', ownedHost, docs)).toBe('https://www.flind.example/docs')
        expect(flindPublicUrl('roadmap', ownedHost, { roadmap: 'https://www.flind.example/roadmap?view=public' })).toBe(
            'https://www.flind.example/roadmap?view=public'
        )
    })

    it.each([
        'https://posthog.com/docs',
        'https://www.flind.example.attacker.com/docs',
        'http://www.flind.example/docs',
        'https://user@www.flind.example/docs',
        'https://www.flind.example:8443/docs',
        'https://www.flind.example/docs#external',
        '//www.flind.example/docs',
        'javascript:alert(1)',
        'https://www.flind.example/docs ',
        'not a url',
    ])('refuses untrusted or malformed page destination %s', (url) => {
        expect(flindPublicUrl('docs', ownedHost, { docs: url })).toBeNull()
    })

    it.each(['', 'WWW.FLIND.EXAMPLE', 'www..flind.example', '-bad.flind.example', 'flind.example/path'])(
        'refuses invalid configured site host %s',
        (host) => {
            expect(flindPublicUrl('docs', host, docs)).toBeNull()
        }
    )
})
