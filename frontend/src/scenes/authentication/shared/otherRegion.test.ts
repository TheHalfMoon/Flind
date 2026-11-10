import { otherRegionLoginUrl, otherRegionOf } from 'scenes/authentication/shared/otherRegion'

import { Region } from '~/types'

const ownedRegions = {
    [Region.US]: 'us.flind.example',
    [Region.EU]: 'eu.flind.example',
}

describe('otherRegion', () => {
    test.each([
        ['US points to EU', Region.US, Region.EU],
        ['EU points to US', Region.EU, Region.US],
    ])('otherRegionOf: %s', (_name, region, expected) => {
        expect(otherRegionOf(region)).toEqual(expected)
    })

    test.each([
        ['US with no query lands on configured EU', Region.US, '', 'https://eu.flind.example/login'],
        ['EU with no query lands on configured US', Region.EU, '', 'https://us.flind.example/login'],
        ['preserves next query parameter', Region.US, '?next=/home', 'https://eu.flind.example/login?next=/home'],
    ])('otherRegionLoginUrl: %s', (_name, region, search, expected) => {
        expect(otherRegionLoginUrl(region, search, ownedRegions)).toEqual(expected)
    })

    it('refuses an unconfigured remote region instead of guessing another service', () => {
        expect(otherRegionLoginUrl(Region.US, '', {})).toBeNull()
    })
})
