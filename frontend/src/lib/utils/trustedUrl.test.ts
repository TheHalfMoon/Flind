import { isTrustedFlindUrl } from './trustedUrl'

describe('isTrustedFlindUrl', () => {
    it.each([
        ['/static/screenshot.png'],
        ['http://localhost/img.png'],
        ['http://localhost/settings'],
    ])('trusts same-origin %s', (url) => {
        expect(isTrustedFlindUrl(url)).toBe(true)
    })

    it.each([
        ['https://outside.example/img.png'],
        ['https://us.flind.example/img.png'],
        ['https://not-flind.example/img.png'],
        ['https://flind.example.attacker.example/img.png'],
        ['https://localhost/img.png'],
        ['http://localhost:9000/img.png'],
        ['//evil.example/img.png'],
        ['data:image/png;base64,iVBORw0KGgo='],
        ['blob:http://localhost/abc'],
        ['javascript:alert(1)'],
        [''],
        [undefined],
    ])('rejects cross-origin or unsafe %s', (url) => {
        expect(isTrustedFlindUrl(url)).toBe(false)
    })
})
