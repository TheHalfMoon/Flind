import { Link } from '@flind/lemon-ui'

import { flindDocsUrl } from 'lib/flindPublicLinks'
import { urls } from 'scenes/urls'

/** Internal Flind management is always available. Optional documentation is
 * an explicitly configured Flind origin; inherited donor skill links are
 * never shown as if they were Flind-maintained resources.
 */
export function ScoutHelperSkillLinks(): JSX.Element {
    const docsUrl = flindDocsUrl('self-driving/scouts')
    return (
        <span className="text-xs text-muted">
            <Link to={urls.inbox('scouts')}>Manage scouts</Link>
            {docsUrl && (
                <>
                    {' · '}
                    <Link to={docsUrl} target="_blank">
                        Learn more about scouts
                    </Link>
                </>
            )}
        </span>
    )
}
