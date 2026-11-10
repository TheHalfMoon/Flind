import { useActions, useValues } from 'kea'

import { LemonButton } from '@flind/lemon-ui'

import { Logomark } from 'lib/brand'
import { AuthCardTitle } from 'scenes/authentication/shared/authScene/AuthCardTitle'
import { AUTH_NOTES } from 'scenes/authentication/shared/authScene/authNotes'
import { AuthScene, AuthSceneCard } from 'scenes/authentication/shared/authScene/AuthScene'
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
        <AuthScene notes={AUTH_NOTES.credentialReview.default} wide>
            <AuthSceneCard>
                <div className="flex justify-center mb-4">
                    <Logomark size="xl" />
                </div>
                <AuthCardTitle
                    title="One more thing"
                    sub="Your account was set up with the credentials and connected apps below. Review them and revoke anything you don't recognize before continuing."
                />
                <div className="mb-6 text-left">
                    <CredentialsReviewList />
                </div>
                <LemonButton
                    type="primary"
                    size="large"
                    fullWidth
                    center
                    onClick={() => markComplete()}
                    loading={isCompleting}
                    disabledReason={continueDisabledReason}
                    data-attr="credential-review-continue"
                >
                    Continue to Flind
                </LemonButton>
            </AuthSceneCard>
        </AuthScene>
    )
}
