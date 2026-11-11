import { flindPublicUrl } from 'lib/flindPublicLinks'
import { Link } from 'lib/lemon-ui/Link'

export function CreateAccountTerms({ action = 'creating an account' }: { action?: string }): JSX.Element {
    // Flind instances publish their own legal policies; without them, point people to their administrator.
    const termsUrl = flindPublicUrl('terms')
    const privacyUrl = flindPublicUrl('privacy')
    if (!termsUrl || !privacyUrl) {
        return (
            <p className="AuthScene__terms mt-5 mb-0 text-xs leading-relaxed text-tertiary text-center">
                Legal policies for this Flind instance have not been configured. Contact your workspace administrator
                for the applicable terms and privacy information.
            </p>
        )
    }
    return (
        <p className="AuthScene__terms mt-5 mb-0 text-xs leading-relaxed text-tertiary text-center">
            <span>By {action}, you agree to the Flind instance's</span>{' '}
            <Link to={termsUrl} target="_blank">
                Terms of Service ↗
            </Link>{' '}
            <span>and</span>{' '}
            <Link to={privacyUrl} target="_blank">
                Privacy Policy ↗
            </Link>
            <span>.</span>
        </p>
    )
}
