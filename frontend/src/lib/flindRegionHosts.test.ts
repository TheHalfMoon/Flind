import { flindRegionHost, flindRegionUrl } from './flindRegionHosts'

import { Region } from '~/types'

const hosts = {
    [Region.US]: 'us.flind.example',
    [Region.EU]: 'eu.flind.example',
}

describe('Flind region URL boundaries', () => {
    it('has no destinations when the operator has configured none', () => {
        expect(flindRegionHost(Region.US, {})).toBeNull()
        expect(flindRegionUrl(Region.US, '/login', {})).toBeNull()
    })

    it('constructs valid first-party URLs only for configured regions', () => {
        expect(flindRegionUrl(Region.EU, '/login?next=/apps', hosts)).toBe('https://eu.flind.example/login?next=/apps')
        expect(flindRegionHost(Region.DEV, hosts)).toBeNull()
    })

    it.each([
        'https://us.flind.example',
        'US.FLIND.EXAMPLE',
        'user@host.example',
        'us.flind.example:443',
        'us.flind.example/evil',
        'a..example.com',
        '-bad.example.com',
        'bad-.example.com',
        '',
    ])('refuses malformed destination host %s', (host) => {
        expect(flindRegionHost(Region.US, { [Region.US]: host })).toBeNull()
    })

    it('rejects protocol-relative paths and backslash injection', () => {
        expect(flindRegionUrl(Region.US, '//untrusted.example.com', hosts)).toBeNull()
        expect(flindRegionUrl(Region.US, '/\\evil', hosts)).toBeNull()
    })
})
