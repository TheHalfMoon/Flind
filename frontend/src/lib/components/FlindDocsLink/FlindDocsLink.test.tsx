import { render, screen } from '@testing-library/react'

import { FlindDocsLink } from './FlindDocsLink'

describe('first-party help link when docs are not configured', () => {
    it('renders meaningful unlinked text instead of a provider URL', () => {
        render(<FlindDocsLink path="support/javascript-api">API reference</FlindDocsLink>)
        expect(screen.getByText('API reference')).toBeTruthy()
        expect(screen.queryByRole('link', { name: 'API reference' })).toBeNull()
    })

    it('does not emit a browser link for an unconfigured section anchor', () => {
        render(
            <FlindDocsLink path="support/javascript-api" section="user-identification">
                Identity verification
            </FlindDocsLink>
        )
        expect(screen.getByText('Identity verification')).toBeTruthy()
        expect(screen.queryByRole('link', { name: 'Identity verification' })).toBeNull()
    })
})
