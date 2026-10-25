import { useValues } from 'kea'

import { IconGear } from '@posthog/icons'
import { LemonButton, LemonSwitch, Link, Tooltip } from '@flind/lemon-ui'

import { flindPublicUrl } from 'lib/flindPublicLinks'
import { IconBranch } from 'lib/lemon-ui/icons/icons'
import { urls } from 'scenes/urls'
import { userLogic } from 'scenes/userLogic'

import { AvailableFeature } from '~/types'

export const PathCleaningToggle = ({
    value,
    onChange,
}: {
    value: boolean
    onChange: (enabled: boolean) => void
}): JSX.Element | null => {
    const { hasAvailableFeature } = useValues(userLogic)
    const hasAdvancedPaths = hasAvailableFeature(AvailableFeature.PATHS_ADVANCED)
    const docsUrl = flindPublicUrl('docs')

    if (!hasAdvancedPaths) {
        return null
    }

    return (
        <Tooltip
            title={
                <div className="p-2">
                    <p className="mb-2">
                        Path cleaning helps standardize URLs by removing unnecessary parameters and fragments.
                    </p>
                    {docsUrl && (
                        <div className="mb-2">
                            <Link to={docsUrl}>Learn more about path cleaning rules</Link>
                        </div>
                    )}
                    <LemonButton
                        icon={<IconGear />}
                        type="primary"
                        size="small"
                        to={urls.settings('project-product-analytics', 'path-cleaning')}
                        targetBlank
                        className="w-full"
                    >
                        Edit path cleaning settings
                    </LemonButton>
                </div>
            }
            placement="top"
            interactive={true}
        >
            <LemonButton icon={<IconBranch />} onClick={() => onChange(!value)} type="secondary" size="small">
                Path cleaning: <LemonSwitch checked={value} className="ml-1" />
            </LemonButton>
        </Tooltip>
    )
}
