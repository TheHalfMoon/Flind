import { isValidElement } from 'react'

import { renderDetailWithLinks } from 'lib/utils/renderDetailWithLinks'

describe('renderDetailWithLinks', () => {
    const linkedUrls = (detail: string): string[] =>
        renderDetailWithLinks(detail)
            .filter((part): part is JSX.Element => isValidElement(part))
            .map((el) => (el.props as { to: string }).to)

    it.each([
        ['links a Flind same-origin path', 'see http://localhost/docs/x for help', ['http://localhost/docs/x']],
        ['does not link a different Flind region', 'visit https://eu.flind.example/foo now', []],
        [
            'strips trailing punctuation from a same-origin href',
            'read http://localhost/docs/x.',
            ['http://localhost/docs/x'],
        ],
        ['leaves inherited provider links as untrusted plain text', 'visit https://posthog.com/docs/x', []],
        ['leaves an external URL as plain text', 'go to https://evil.example.com/phish', []],
        ['leaves a lookalike host as plain text', 'open http://localhost.evil.com/x here', []],
        ['does not link a different port', 'open http://localhost:8010/details', []],
        ['renders plain detail with no links', 'This query ran out of memory.', []],
    ])('%s', (_name, detail, expected) => {
        expect(linkedUrls(detail)).toEqual(expected)
    })
})
