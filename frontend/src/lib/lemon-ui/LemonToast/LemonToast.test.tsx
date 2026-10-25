import '@testing-library/jest-dom'

import { act, fireEvent, render, within } from '@testing-library/react'
import posthog from 'posthog-js'

import { resetGetHelpAction, setGetHelpAction } from './getHelp'
import { GET_HELP_BUTTON, ToastContent, lemonToast, withClickableUrls } from './LemonToast'

const mockPosthog = posthog as unknown as { __loaded: boolean; capture: jest.Mock }

describe('LemonToast', () => {
    const writeText = jest.fn((_text: string) => Promise.resolve())

    beforeEach(() => {
        jest.clearAllMocks()
        Object.assign(navigator, { clipboard: { writeText } })
    })

    afterEach(() => {
        resetGetHelpAction()
        jest.restoreAllMocks()
    })

    // "Get help" has to reach support where the person already is. Sending them to posthog.com
    // instead drops the error, the scene, and everything else that made the toast worth acting on.
    it('runs the registered get-help action rather than opening posthog.com', () => {
        const openSupport = jest.fn()
        setGetHelpAction(openSupport)
        const windowOpen = jest.spyOn(window, 'open').mockImplementation(() => null)

        const { container } = render(
            <ToastContent type="error" message="Load experiment failed" button={GET_HELP_BUTTON} />
        )
        fireEvent.click(within(container).getByText('Get help'))

        expect(openSupport).toHaveBeenCalledTimes(1)
        expect(windowOpen).not.toHaveBeenCalled()
    })

    // Without a configured Flind-owned docs host, help never opens a vendor fallback.
    it('does not open inherited vendor docs when no owned docs are configured', () => {
        const windowOpen = jest.spyOn(window, 'open').mockImplementation(() => null)

        const { container } = render(
            <ToastContent type="error" message="Load experiment failed" button={GET_HELP_BUTTON} />
        )
        fireEvent.click(within(container).getByText('Get help'))

        expect(windowOpen).not.toHaveBeenCalled()
    })

    // The copy button reads the rendered message out of the DOM, so it copies whatever sits inside the
    // message element. Widening that element to cover the action button would silently append "Get help"
    // to every error someone pastes elsewhere.
    it('copies the message without the action button label', async () => {
        const { container } = render(
            <ToastContent type="error" message="Load experiment failed" button={GET_HELP_BUTTON} />
        )

        fireEvent.click(container.querySelector('[data-attr="toast-copy-button"]')!)
        await act(async () => {})

        expect(writeText).toHaveBeenCalledWith('Load experiment failed')
    })

    it.each([
        ['error', true],
        ['warning', true],
        ['info', false],
        ['success', false],
    ] as const)('renders the copy button on a %s toast: %s', (type, expected) => {
        const { container } = render(<ToastContent type={type} message="A message" />)

        expect(!!container.querySelector('[data-attr="toast-copy-button"]')).toBe(expected)
    })

    // Only owned same-origin URLs are linked, never an inherited vendor URL.
    it('leaves inherited vendor documentation URLs as plain text', () => {
        const { container } = render(
            <>{withClickableUrls('Visit https://posthog.com/docs to fix this, then retry.')}</>
        )

        expect(container.querySelector('a')).toBeNull()
        expect(container).toHaveTextContent('Visit https://posthog.com/docs to fix this, then retry.')
    })

    it('links Flind same-origin documentation URLs without rewriting the message', () => {
        const docsUrl = `${window.location.origin}/docs`
        const { container } = render(<>{withClickableUrls(`Visit ${docsUrl} for help.`)}</>)
        expect(container.querySelector('a')).toHaveAttribute('href', docsUrl)
        expect(container).toHaveTextContent(`Visit ${docsUrl} for help.`)
    })

    it('leaves a URL outside posthog.com as plain text', () => {
        const { container } = render(<>{withClickableUrls('More info: https://example.com/details')}</>)

        expect(container.querySelector('a')).toBeNull()
        expect(container).toHaveTextContent('More info: https://example.com/details')
    })

    it('returns a message without URLs unchanged', () => {
        expect(withClickableUrls('Load experiment failed')).toBe('Load experiment failed')
    })

    // The toolbar bundle imports this default instance but initializes a named one, so the guard has
    // to read __loaded. `capture` is a class method, so checking for it lets the call through.
    it.each([
        { name: 'reports a warning toast on an initialized instance', type: 'warning', event: 'toast warning' },
        { name: 'reports an error toast on an initialized instance', type: 'error', event: 'toast error' },
        { name: 'stays quiet for a warning toast on an uninitialized instance', type: 'warning', event: null },
        { name: 'stays quiet for an error toast on an uninitialized instance', type: 'error', event: null },
    ] as const)('$name', ({ type, event }) => {
        mockPosthog.__loaded = event !== null

        lemonToast[type]('Load experiment failed')

        expect(mockPosthog.capture.mock.calls.map(([name]) => name)).toEqual(event ? [event] : [])
    })
})
