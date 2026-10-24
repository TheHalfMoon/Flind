import { useActions, useValues } from 'kea'

import { LemonButton } from '@flind/lemon-ui'

import { Logomark } from 'lib/brand'
import { BridgePage } from 'lib/components/BridgePage/BridgePage'
import { SceneExport } from 'scenes/sceneTypes'

import { credentialReviewLogic } from './credentialReviewLogic'
import { CredentialsReviewList } from './CredentialsReviewList'

export const scene: SceneExport = {
    component: CredentialReview,
    logic: credentialReviewLogic,
}


export function CredentialReview(): JSX.Element {
    const { markComplete } = useActions(credentialReviewLogic)
    const { continueDisabledReason, isCompleting } = useValues(credentialReviewLogic)

    return (
        <BridgePage view="credential-review" fixedWidth={false}>
            <div className="px-12 py-8 flex flex-col items-center max-w-3xl w-full text-center">
                <h2 className="text-lg">Welcome to Flind!</h2>
                <h1 className="text-3xl font-bold">One more thing.</h1>
                <div className="max-w-60 my-8">
                    <Logomark size="xl" />
                </div>
                <p className="mb-6 max-w-xl">
                    Your account was set up with the credentials and connected apps listed below. Review them and revoke
                    anything you don't recognize before continuing.
                </p>
                <div className="w-full mb-6 text-left">
                    <CredentialsReviewList />
                </div>
                <LemonButton
                    type="primary"
                    size="large"
                    onClick={() => markComplete()}
                    loading={isCompleting}
                    disabledReason={continueDisabledReason}
                    data-attr="credential-review-continue"
                >
                    Continue to Flind
                </LemonButton>
            </div>
        </BridgePage>
    )
}
