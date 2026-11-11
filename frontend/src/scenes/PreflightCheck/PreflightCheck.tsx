import './PreflightCheck.scss'

import clsx from 'clsx'
import { useActions, useValues } from 'kea'

import { IconCheckCircle, IconCollapse, IconExpand, IconRefresh, IconWarning } from '@flind/icons'
import { Link, Spinner } from '@flind/lemon-ui'

import { AnimatedCollapsible } from 'lib/components/AnimatedCollapsible'
import { flindPublicUrl } from 'lib/flindPublicLinks'
import { IconErrorOutline } from 'lib/lemon-ui/icons'
import { LemonButton } from 'lib/lemon-ui/LemonButton'
import { LemonDivider } from 'lib/lemon-ui/LemonDivider'
import { LemonRow } from 'lib/lemon-ui/LemonRow'
import { PreflightCheckStatus, PreflightItem, preflightLogic } from 'lib/logic/preflightLogic'
import { capitalizeFirstLetter } from 'lib/utils/strings'
import { AUTH_NOTES } from 'scenes/authentication/shared/authScene/authNotes'
import { AuthScene, AuthSceneCard } from 'scenes/authentication/shared/authScene/AuthScene'
import { SceneExport } from 'scenes/sceneTypes'

export const scene: SceneExport = {
    component: PreflightCheck,
    logic: preflightLogic,
}

function PreflightCheckIcon({ status, loading }: { status: PreflightCheckStatus; loading?: boolean }): JSX.Element {
    if (loading) {
        return <Spinner textColored className="text-accent" />
    }
    if (status === 'validated') {
        return <IconCheckCircle />
    } else if (status === 'warning' || status === 'optional') {
        return <IconWarning />
    }
    return <IconErrorOutline />
}

function PreflightItemRow({ name, status, caption }: PreflightItem): JSX.Element {
    const { preflightLoading } = useValues(preflightLogic)
    return (
        <div className={clsx('PreflightItem', preflightLoading ? 'Preflight--loading' : `Preflight--${status}`)}>
            <div className="PreflightItem__icon-container">
                <PreflightCheckIcon status={status} loading={preflightLoading} />
            </div>
            <div className="PreflightItem__text-container">
                <p className="PreflightItem__item-name">{name}</p>
                {caption && (
                    <p data-attr="caption" className="text-secondary">
                        {caption}
                    </p>
                )}
            </div>

            <div>
                <p className="Preflight__status-text" data-attr="status-text">
                    {capitalizeFirstLetter(preflightLoading ? 'checking' : status)}
                </p>
            </div>
        </div>
    )
}

export function PreflightCheck(): JSX.Element {
    const { preflight, preflightLoading, preflightMode, checks, areChecksExpanded, checksSummary } =
        useValues(preflightLogic)
    const { setPreflightMode, handlePreflightFinished, setChecksManuallyExpanded, revalidatePreflight } =
        useActions(preflightLogic)
    const docsUrl = flindPublicUrl('docs')
    const communityUrl = flindPublicUrl('community')

    const linkClassName =
        'font-semibold no-underline cursor-pointer hover:underline hover:underline-offset-2 text-warning'
    const footer = (
        <p className="mt-5 mb-0 text-sm text-secondary text-center">
            {docsUrl || communityUrl ? (
                <>
                    <span>Need help?</span>{' '}
                    {docsUrl && (
                        <Link to={docsUrl} target="_blank" targetBlankIcon={false} className={linkClassName}>
                            Flind documentation
                        </Link>
                    )}
                    {docsUrl && communityUrl && <span> or </span>}
                    {communityUrl && (
                        <Link to={communityUrl} target="_blank" targetBlankIcon={false} className={linkClassName}>
                            Flind community
                        </Link>
                    )}
                    <span>.</span>
                </>
            ) : (
                <span>Need help? Contact your Flind workspace administrator.</span>
            )}
        </p>
    )

    return (
        <AuthScene notes={AUTH_NOTES.preflight.default}>
            <AuthSceneCard footer={footer}>
                <div className="Preflight">
                    {!preflightMode ? (
                        <>
                            <div className="Preflight__header">
                                <p className="Preflight__header--title-text">Select a launch mode</p>
                                <p className="Preflight__header--secondary-text">
                                    What's your plan for this installation? We'll make infrastructure checks
                                    accordingly.
                                </p>
                            </div>
                            <LemonButton
                                fullWidth
                                center
                                type="primary"
                                className="mt-2"
                                size="large"
                                data-attr="preflight-live"
                                onClick={() => setPreflightMode('live')}
                            >
                                Live implementation
                            </LemonButton>
                            <LemonButton
                                type="secondary"
                                fullWidth
                                center
                                className="mt-2"
                                size="large"
                                data-attr="preflight-experimentation"
                                onClick={() => setPreflightMode('experimentation')}
                            >
                                Just experimenting
                            </LemonButton>
                            <LemonDivider thick dashed className="my-6" />
                            <p className="text-secondary text-center mb-0">
                                We will not enforce some security requirements in experimentation mode.
                            </p>
                        </>
                    ) : (
                        <>
                            <div className="Preflight__header">
                                <p className="Preflight__header--title-text">Validate implementation</p>
                                <p className="Preflight__header--secondary-text">
                                    Validation happens immediately. You can rerun checks using “Validate requirements”.
                                    If validation fails,{' '}
                                    {docsUrl ? (
                                        <Link to={docsUrl} target="_blank">
                                            consult the Flind documentation
                                        </Link>
                                    ) : (
                                        'contact your Flind workspace administrator'
                                    )}
                                    .
                                </p>
                            </div>

                            <div className="Preflight__checks-container">
                                <div className="Preflight__check-summary">
                                    <div
                                        className={clsx(
                                            'Preflight__summary-icon-container',
                                            preflightLoading
                                                ? 'Preflight--loading'
                                                : `Preflight--${checksSummary.summaryStatus}`
                                        )}
                                    >
                                        <PreflightCheckIcon
                                            status={checksSummary.summaryStatus}
                                            loading={preflightLoading}
                                        />
                                    </div>
                                    <div className="Preflight__summary-text-container">
                                        <p className="Preflight__summary-header">Validation checks</p>
                                        <p
                                            data-attr="caption"
                                            className="text-secondary Preflight__summary-description"
                                        >
                                            {checksSummary.summaryString}
                                        </p>
                                    </div>
                                    <LemonButton
                                        icon={
                                            areChecksExpanded ? (
                                                <IconCollapse style={{ color: 'var(--color-text-secondary)' }} />
                                            ) : (
                                                <IconExpand style={{ color: 'var(--color-text-secondary)' }} />
                                            )
                                        }
                                        onClick={() => {
                                            setChecksManuallyExpanded(!areChecksExpanded)
                                        }}
                                    />
                                </div>
                                <AnimatedCollapsible collapsed={!areChecksExpanded}>
                                    <>
                                        {checks.map((item) => (
                                            <PreflightItemRow key={item.id} {...item} />
                                        ))}
                                    </>
                                </AnimatedCollapsible>
                                <LemonButton
                                    center
                                    fullWidth
                                    size="large"
                                    data-attr="preflight-refresh"
                                    onClick={() => revalidatePreflight()}
                                    disabled={preflightLoading || !preflight}
                                    icon={<IconRefresh />}
                                >
                                    Validate requirements
                                </LemonButton>
                            </div>
                            <LemonDivider thick dashed className="my-6" />
                            {checksSummary.summaryStatus !== 'error' || preflightMode == 'experimentation' ? (
                                <LemonButton
                                    fullWidth
                                    center
                                    type="primary"
                                    className="mt-2"
                                    size="large"
                                    data-attr="preflight-complete"
                                    onClick={handlePreflightFinished}
                                >
                                    Continue
                                </LemonButton>
                            ) : (
                                <LemonRow fullWidth center className="mt-2 Preflight__cannot-continue" size="large">
                                    <p className="text-center text-secondary">
                                        All required checks must pass before you can continue
                                    </p>
                                </LemonRow>
                            )}
                        </>
                    )}
                </div>
            </AuthSceneCard>
        </AuthScene>
    )
}

export default PreflightCheck
