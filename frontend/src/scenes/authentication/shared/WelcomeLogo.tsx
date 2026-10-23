import { Link } from '@posthog/lemon-ui'

import { Logo } from 'lib/brand'

// Keep the existing component API while making the link stay in this Flind instance.
export function WelcomeLogo(_props: { view?: string }): JSX.Element {
    return (
        <Link to="/" className="flex flex-col items-center mb-8" aria-label="Flind home">
            <Logo size="md" className="shrink-0" aria-hidden />
        </Link>
    )
}
