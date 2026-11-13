import * as React from 'react'
import { render, act } from '@testing-library/react'
import { PostHogProvider, PostHog } from '..'
import posthogJs from 'posthog-js'
import { setDefaultPostHogInstance } from '../posthog-default'

// Mock posthog-js
vi.mock('posthog-js', () => ({
    __esModule: true,
    default: {
        init: vi.fn(),
        set_config: vi.fn(),
        opt_out_capturing: vi.fn(),
        __loaded: false,
    },
}))

describe('PostHogProvider component', () => {
    beforeEach(() => {
        setDefaultPostHogInstance(posthogJs)
    })

    afterEach(() => {
        setDefaultPostHogInstance(undefined)
    })

    it('should render children components', () => {
        const posthog = {} as unknown as PostHog
        const { getByText } = render(
            <PostHogProvider client={posthog}>
                <div>Test</div>
            </PostHogProvider>
        )
        expect(getByText('Test')).toBeTruthy()
    })

    describe('when using apiKey initialization', () => {
        const apiKey = 'test-api-key'
        const initialOptions = { api_host: 'https://collector.flind.example' }
        const updatedOptions = { api_host: 'https://other.flind.example' }

        beforeEach(() => {
            vi.clearAllMocks()
        })

        it('does not initialize when apiKey is missing', () => {
            const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

            render(
                <PostHogProvider apiKey={undefined as any} options={initialOptions}>
                    <div>Test</div>
                </PostHogProvider>
            )

            expect(posthogJs.init).not.toHaveBeenCalled()
            expect(consoleSpy).toHaveBeenCalledWith(
                '[PostHog.js] No `apiKey` or `client` were provided to `PostHogProvider`. Using default global `window.posthog` instance. You must initialize it manually. This is not recommended behavior.'
            )

            consoleSpy.mockRestore()
        })

        it('should call set_config when options change', () => {
            const { rerender } = render(
                <PostHogProvider apiKey={apiKey} options={initialOptions}>
                    <div>Test</div>
                </PostHogProvider>
            )

            // First render should initialize
            expect(posthogJs.init).toHaveBeenCalledWith(apiKey, { ...initialOptions, ui_host: initialOptions.api_host })

            // Rerender with new options
            act(() => {
                rerender(
                    <PostHogProvider apiKey={apiKey} options={updatedOptions}>
                        <div>Test</div>
                    </PostHogProvider>
                )
            })

            // Should call set_config with new options
            expect(posthogJs.set_config).toHaveBeenCalledWith({ ...updatedOptions, ui_host: updatedOptions.api_host })
        })

        it('should NOT call set_config when we pass new options that are the same as the previous options', () => {
            const { rerender } = render(
                <PostHogProvider apiKey={apiKey} options={initialOptions}>
                    <div>Test</div>
                </PostHogProvider>
            )

            // First render should initialize
            expect(posthogJs.init).toHaveBeenCalledWith(apiKey, { ...initialOptions, ui_host: initialOptions.api_host })

            // Rerender with new options
            const sameOptionsButDifferentReference = { ...initialOptions }
            act(() => {
                rerender(
                    <PostHogProvider apiKey={apiKey} options={sameOptionsButDifferentReference}>
                        <div>Test</div>
                    </PostHogProvider>
                )
            })

            // Should NOT call set_config
            expect(posthogJs.set_config).not.toHaveBeenCalled()
        })

        it('should warn when attempting to change apiKey', () => {
            const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
            const newApiKey = 'different-api-key'

            const { rerender } = render(
                <PostHogProvider apiKey={apiKey} options={initialOptions}>
                    <div>Test</div>
                </PostHogProvider>
            )

            // First render should initialize
            expect(posthogJs.init).toHaveBeenCalledWith(apiKey, { ...initialOptions, ui_host: initialOptions.api_host })

            // Rerender with new apiKey
            act(() => {
                rerender(
                    <PostHogProvider apiKey={newApiKey} options={initialOptions}>
                        <div>Test</div>
                    </PostHogProvider>
                )
            })

            expect(posthogJs.init).toHaveBeenCalledTimes(1)
            expect(posthogJs.init).toHaveBeenLastCalledWith(apiKey, { ...initialOptions, ui_host: initialOptions.api_host })
            // Should warn about apiKey change
            expect(consoleSpy).toHaveBeenCalledWith(
                expect.stringContaining('You have provided a different `apiKey` to `PostHogProvider`')
            )

            consoleSpy.mockRestore()
        })

        it.each([
            undefined,
            '',
            'https://us.i.posthog.com',
            'https://app.posthog.com',
            'http://collector.flind.example',
            'https://collector.flind.example/path',
            'https://user:secret@collector.flind.example',
        ])('does not initialize the client without a safe Flind-owned collector: %s', (host) => {
            const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
            render(
                <PostHogProvider apiKey={apiKey} options={{ api_host: host as string }}>
                    <div>Test</div>
                </PostHogProvider>
            )
            expect(posthogJs.init).not.toHaveBeenCalled()
            expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('analytics disabled'))
            consoleSpy.mockRestore()
        })

        it('opts out rather than changing to an inherited host after initialization', () => {
            const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
            const { rerender } = render(
                <PostHogProvider apiKey={apiKey} options={initialOptions}>
                    <div>Test</div>
                </PostHogProvider>
            )
            expect(posthogJs.init).toHaveBeenCalledOnce()
            act(() => {
                rerender(
                    <PostHogProvider apiKey={apiKey} options={{ api_host: 'https://eu.posthog.com' }}>
                        <div>Test</div>
                    </PostHogProvider>
                )
            })
            expect(posthogJs.opt_out_capturing).toHaveBeenCalledOnce()
            expect(posthogJs.set_config).not.toHaveBeenCalled()
            consoleSpy.mockRestore()
        })

        it('warns if posthogJs has been loaded elsewhere', () => {
            ;(posthogJs as any).__loaded = true

            const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
            render(
                <PostHogProvider apiKey={apiKey} options={initialOptions}>
                    <div>Test</div>
                </PostHogProvider>
            )

            expect(consoleSpy).toHaveBeenCalledWith(
                expect.stringContaining('`posthog` was already loaded elsewhere. This may cause issues.')
            )

            consoleSpy.mockRestore()
            ;(posthogJs as any).__loaded = false
        })
    })
})
