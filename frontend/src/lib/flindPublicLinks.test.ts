import { flindDocsUrl, flindPublicUrl } from './flindPublicLinks'

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
    it('rejects unconfigured terms and privacy URLs', () => {
        expect(flindPublicUrl('terms', ownedHost, {})).toBeNull()
        expect(flindPublicUrl('privacy', ownedHost, {})).toBeNull()
    })

    it('accepts only first-party operator-configured legal pages', () => {
        const legal = {
            terms: 'https://www.flind.example/terms',
            privacy: 'https://www.flind.example/privacy',
        }
        expect(flindPublicUrl('terms', ownedHost, legal)).toBe(legal.terms)
        expect(flindPublicUrl('privacy', ownedHost, legal)).toBe(legal.privacy)
        expect(flindPublicUrl('terms', ownedHost, { terms: 'https://unowned.example/terms' })).toBeNull()
        expect(
            flindPublicUrl('privacy', ownedHost, { privacy: 'https://www.flind.example.evil.com/privacy' })
        ).toBeNull()
    })
})

describe('Flind deep documentation URLs', () => {
    const host = 'www.flind.example'
    const ownedDocs = { docs: 'https://www.flind.example/docs' }

    it('appends nested first-party pages under the configured docs root', () => {
        expect(flindDocsUrl('support/widget', host, ownedDocs)).toBe('https://www.flind.example/docs/support/widget')
        expect(flindDocsUrl('self-driving/scouts', host, ownedDocs)).toBe(
            'https://www.flind.example/docs/self-driving/scouts'
        )
        expect(flindDocsUrl('support', host, { docs: 'https://www.flind.example/docs/' })).toBe(
            'https://www.flind.example/docs/support'
        )
    })

    it('fails closed when docs are not configured or point at another provider', () => {
        expect(flindDocsUrl('support', '', ownedDocs)).toBeNull()
        expect(flindDocsUrl('support', host, {})).toBeNull()
        expect(flindDocsUrl('support', host, { docs: 'https://posthog.com/docs' })).toBeNull()
        expect(flindDocsUrl('support', host, { docs: 'https://www.flind.example.evil.com/docs' })).toBeNull()
    })

    it.each([
        '',
        '/support',
        '//attacker.example',
        '../support',
        'support/../private',
        'support//widget',
        'support/',
        'support?next=https://attacker.example',
        'support#identity',
        'https://posthog.com/docs/support',
        '%2F%2Fattacker',
        'support\\widget',
        'SUPPORT',
        ' support',
        'support ',
    ])('refuses unsafe relative docs path %s', (path) => {
        expect(flindDocsUrl(path, host, ownedDocs)).toBeNull()
    })

    it('rejects untyped input without throwing or opening a link', () => {
        for (const invalid of [null, 42, {}, ['support']]) {
            expect(flindDocsUrl(invalid as unknown as string, host, ownedDocs)).toBeNull()
        }
    })

    it('does not retain a configured query in a generated deep link', () => {
        expect(flindDocsUrl('support', host, { docs: 'https://www.flind.example/docs?ref=site' })).toBe(
            'https://www.flind.example/docs/support'
        )
    })
})
