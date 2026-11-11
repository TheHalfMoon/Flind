import { IconLock } from '@flind/icons'

import { flindPublicUrl } from 'lib/flindPublicLinks'
import { Link } from 'lib/lemon-ui/Link'

export function GroupsIntroductionOption(): JSX.Element {
    const docsUrl = flindPublicUrl('docs')
    return (
        <div className="cursor-default">
            <IconLock style={{ marginRight: 6, color: 'var(--warning)' }} />
            Unique groups
            {docsUrl && (
                <>
                    {' – '}
                    <Link
                        to={docsUrl}
                        target="_blank"
                        data-attr="group-analytics-learn-more"
                        className="font-semibold"
                    >
                        View documentation
                    </Link>
                </>
            )}
        </div>
    )
}
