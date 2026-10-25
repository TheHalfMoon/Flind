import { render, screen } from '@testing-library/react'

import { SessionAnalysisWarning } from './SessionAnalysisWarning'

describe('SessionAnalysisWarning first-party docs fallback', () => {
    it('preserves warning text without linking to a donor when docs are unconfigured', () => {
        const { container } = render(<SessionAnalysisWarning />)
        expect(container.textContent).toContain('events without session IDs will be excluded')
        expect(container.textContent).toContain('Learn more about sessions.')
        expect(screen.queryByRole('link', { name: 'Learn more about sessions.' })).toBeNull()
    })
})
