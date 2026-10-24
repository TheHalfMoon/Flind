import { flindPublicUrl } from 'lib/flindPublicLinks'

import { getHelp, openSupportOptions, resetGetHelpAction, setGetHelpAction } from './getHelp'

jest.mock('lib/flindPublicLinks', () => ({
    flindPublicUrl: jest.fn(),
}))

const mockFlindPublicUrl = flindPublicUrl as jest.MockedFunction<typeof flindPublicUrl>

describe('Flind error-toast help fallback', () => {
    let openSpy: jest.SpyInstance

    beforeEach(() => {
        mockFlindPublicUrl.mockReturnValue(null)
        openSpy = jest.spyOn(window, 'open').mockImplementation(() => null)
        resetGetHelpAction()
    })

    afterEach(() => {
        resetGetHelpAction()
        jest.restoreAllMocks()
        jest.clearAllMocks()
    })

    it('does not navigate to an inherited help site when Flind docs are unconfigured', () => {
        getHelp()
        expect(mockFlindPublicUrl).toHaveBeenCalledWith('docs')
        expect(openSpy).not.toHaveBeenCalled()
    })

    it('opens an explicitly configured Flind docs URL with safely encoded campaign metadata', () => {
        mockFlindPublicUrl.mockReturnValue('https://docs.flind.example/help?source=app')
        openSupportOptions('widget & error#1')

        expect(openSpy).toHaveBeenCalledTimes(1)
        const [url, target, features] = openSpy.mock.calls[0] as [string, string, string]
        const parsed = new URL(url)
        expect(parsed.origin).toBe('https://docs.flind.example')
        expect(parsed.pathname).toBe('/help')
        expect(parsed.searchParams.get('source')).toBe('app')
        expect(parsed.searchParams.get('utm_medium')).toBe('in-product')
        expect(parsed.searchParams.get('utm_campaign')).toBe('widget & error#1')
        expect(target).toBe('_blank')
        expect(features).toBe('noopener,noreferrer')
    })

    it('uses the same approved documentation destination for default campaigns', () => {
        mockFlindPublicUrl.mockReturnValue('https://docs.flind.example/support')
        getHelp()
        const [url] = openSpy.mock.calls[0] as [string]
        expect(new URL(url).searchParams.get('utm_campaign')).toBe('error-toast')
    })

    it('keeps the first-party in-app support registration working', () => {
        const customAction = jest.fn()
        setGetHelpAction(customAction)
        getHelp()
        expect(customAction).toHaveBeenCalledTimes(1)
        expect(openSpy).not.toHaveBeenCalled()
    })
})
