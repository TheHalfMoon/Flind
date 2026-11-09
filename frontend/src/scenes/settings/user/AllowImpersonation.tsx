import { useActions, useValues } from 'kea'

import { LemonSwitch, Link } from '@flind/lemon-ui'

import { userLogic } from 'scenes/userLogic'

export function AllowImpersonation(): JSX.Element {
    const { user, userLoading } = useValues(userLogic)
    const { updateUser } = useActions(userLogic)

    return (
        <div>
            <p>
                Staff users of this Flind instance may need to log in as you to help debug issues. If you disable this setting,
                staff users will not be able to access your account directly. See the upstream{' '}
                <Link to="https://posthog.com/handbook/company/security#impersonating-users" target="_blank">
                    policy on user impersonation
                </Link>
                .
            </p>
            <LemonSwitch
                label="Allow support to log in as me"
                data-attr="allow-impersonation"
                onChange={(checked) => updateUser({ allow_impersonation: checked })}
                checked={user?.allow_impersonation ?? true}
                disabled={userLoading}
                bordered
            />
        </div>
    )
}
