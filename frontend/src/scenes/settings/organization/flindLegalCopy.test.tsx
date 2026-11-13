import { cleanup, render, screen } from '@testing-library/react'

import { SDKSnippet } from 'scenes/onboarding/sdks/SDKSnippet'

import { SDK, SDKKey, SDKTag } from '~/types'

import { AIHipaaDisclaimer } from './aiConsentCopy'
import { AITrainingDescription } from './OrgAITraining'

// Flind is self-hosted software, not a contracting party. Copy must not claim a BAA, DPA or data
// custody relationship "with Flind", and must not mislabel inherited SDKs or their documentation.
const FLIND_LEGAL_CLAIM = /(BAA|DPA|agreement|subprocessor)[^.]*with Flind|stays with Flind|Flind subprocessors/i

describe('Flind legal and data-handling copy', () => {
    afterEach(() => cleanup())

    it.each([
        ['signed BAA', { hasSignedBaa: true, isLocked: false }, /your organization has a signed BAA/],
        ['locked by contract', { hasSignedBaa: false, isLocked: true }, /Contact your Flind administrator/],
        ['default opt-in copy', { hasSignedBaa: false, isLocked: false }, /depends on how this Flind instance is operated/],
    ])('AI training copy for %s states only what the deployment supports', (_, props, expected) => {
        const { container } = render(<AITrainingDescription {...props} />)

        expect(container.textContent).toMatch(expected)
        expect(container.textContent).not.toMatch(FLIND_LEGAL_CLAIM)
    })

    it('HIPAA disclaimer refers to the deployment, not to an agreement with Flind', () => {
        const { container } = render(<AIHipaaDisclaimer />)

        expect(container.textContent).toMatch(/BAA.*covers your deployment does not apply/)
        expect(container.textContent).not.toMatch(FLIND_LEGAL_CLAIM)
    })

    it('SDK onboarding uses neutral labels until SDK packages are Flind-branded', () => {
        const sdk: SDK = {
            name: 'React',
            key: SDKKey.REACT,
            tags: [SDKTag.WEB],
            image: '',
            docsLink: 'https://example.test/docs/react',
        }

        render(<SDKSnippet sdk={sdk} sdkInstructions={() => <div />} />)

        expect(screen.getByRole('heading', { name: 'Send React data to Flind using the integration SDK' })).toBeTruthy()
        expect(screen.queryByRole('link', { name: 'Read the Flind SDK documentation' })).toBeNull()
        expect(screen.getByText('SDK documentation is not configured for this Flind instance.')).toBeTruthy()
    })
})
