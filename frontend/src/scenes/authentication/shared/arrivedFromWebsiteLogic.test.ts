import { setDocumentReferrer } from './authReferrer.mock'

import { expectLogic } from 'kea-test-utils'

import { initKeaTests } from '~/test/init'

import { arrivedFromWebsiteLogic, isWebsiteReferrer } from './arrivedFromWebsiteLogic'

describe('arrivedFromWebsiteLogic', () => {
    beforeEach(() => {
        initKeaTests()
        setDocumentReferrer('')
    })

    it.each([
        ['https://flind.example/', true],
        ['https://flind.example/pricing', true],
        ['https://flind.example/docs/getting-started', true],
        ['', false],
        ['http://flind.example/', false],
        ['https://otherproduct.example/', false],
        ['https://flind.example.phishing.example/', false],
        ['https://example.com/?ref=https://flind.example/', false],
        ['not-a-url', false],
    ])('reads %p as arrived-from-website %p for an explicitly configured Flind host', (referrer, expected) => {
        expect(isWebsiteReferrer(referrer, 'flind.example')).toBe(expected)
    })

    it('has no trusted marketing website unless explicitly configured', () => {
        expect(isWebsiteReferrer('https://flind.example/', '')).toBe(false)
        expect(isWebsiteReferrer('https://flind.example/', 'evil@flind.example')).toBe(false)
    })

    it('defaults to untrusted for website referrers on an unconfigured Flind instance', async () => {
        setDocumentReferrer('https://flind.example/pricing')
        const logic = arrivedFromWebsiteLogic()
        logic.mount()
        await expectLogic(logic).toMatchValues({ arrivedFromWebsite: false })
    })
})
