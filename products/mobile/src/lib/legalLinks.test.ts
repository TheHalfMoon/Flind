import { Linking } from 'react-native'

import { openLegalLink, ownedLegalUrl } from './legalLinks'

describe('operator-owned Flind legal destinations', () => {
    test.each([
        [undefined, null],
        ['', null],
        ['http://privacy.flind.example/policy', null],
        ['https://posthog.com/privacy', null],
        ['https://us.posthog.com/privacy', null],
        ['https://eu.posthog.dev/privacy', null],
        ['https://person:secret@privacy.flind.example/policy', null],
        ['javascript:alert(1)', null],
        ['https://privacy.flind.example', 'https://privacy.flind.example/'],
        ['https://privacy.flind.example/policy', 'https://privacy.flind.example/policy'],
    ])('normalizes only valid, non-inherited HTTPS policy URLs: %s', (input, expected) => {
        expect(ownedLegalUrl(input)).toBe(expected)
    })

    test('an unconfigured policy never initiates a browser navigation', () => {
        const open = jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined)
        try {
            openLegalLink('privacy', null, 'sign_in')
            expect(open).not.toHaveBeenCalled()
        } finally {
            open.mockRestore()
        }
    })
})
