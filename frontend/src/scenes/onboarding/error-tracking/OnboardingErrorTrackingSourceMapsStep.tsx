import { useActions, useValues } from 'kea'

import { EditKeyModal } from 'scenes/settings/user/PersonalAPIKeys'

import { OnboardingStepKey } from '~/types'

import { OnboardingStepComponentType } from '../onboardingLogic'
import { OnboardingStep } from '../OnboardingStep'
import { SourceMapOptionCard } from './source-maps/SourceMapOptionCard'
import { sourceMapsStepLogic } from './source-maps/sourceMapsStepLogic'
import { SourceMapStatus } from './source-maps/SourceMapStatus'

/**
 * Do not offer executable installation, login, or symbol-upload commands until
 * a Flind-owned CLI binary and its upload-host/tenant-isolation checks pass.
 * The inherited installer targets another provider's distribution service.
 */
export const OnboardingErrorTrackingSourceMapsStep: OnboardingStepComponentType = () => {
    const { selectedOption, shouldShowContinue, shouldShowSourceMapStatus } = useValues(sourceMapsStepLogic)
    const { setSelectedOption } = useActions(sourceMapsStepLogic)

    return (
        <OnboardingStep
            title="Link source maps"
            stepKey={OnboardingStepKey.SOURCE_MAPS}
            showContinue={shouldShowContinue}
            showSkip={!shouldShowContinue}
        >
            <p>
                Source maps help transform minified stack traces into readable code. Choose the option that matches
                your application. This optional setup must not send code, symbols or credentials to another provider.
            </p>

            <div className="space-y-3 mt-4">
                <SourceMapOptionCard
                    title="Unminified code"
                    description="Unminified languages such as Python and Node.js can produce readable stack traces without uploading source maps."
                    optionKey="no-minification"
                    selectedOption={selectedOption}
                    onSelect={() => setSelectedOption('no-minification')}
                />
                <SourceMapOptionCard
                    title="Public source maps"
                    description="If source maps are served by your own application, Flind may be able to retrieve them without a private upload."
                    optionKey="public-source-maps"
                    selectedOption={selectedOption}
                    onSelect={() => setSelectedOption('public-source-maps')}
                />
                <SourceMapOptionCard
                    title="Private source maps (Flind CLI not yet available)"
                    description="An independently built and tested Flind CLI is required for private source maps and native debug symbols."
                    optionKey="cli"
                    selectedOption={selectedOption}
                    onSelect={() => setSelectedOption('cli')}
                >
                    <p className="mt-4 text-sm text-muted">
                        Private source-map uploads are not yet available through this setup wizard. Installer,
                        authentication and upload commands are intentionally withheld until the Flind CLI has passed
                        owned-host, authorization, binary integrity and distribution checks. Do not install another
                        provider's CLI or upload private source code to its service as part of Flind setup.
                    </p>
                </SourceMapOptionCard>
            </div>

            <p className="mt-6 text-sm text-muted">
                Automatic source-map and iOS dSYM uploads are also unavailable until the first-party Flind CLI is
                qualified. You can select unminified code, use public source maps, or skip this optional step.
            </p>

            {shouldShowSourceMapStatus && <SourceMapStatus />}
            <EditKeyModal zIndex="1162" />
        </OnboardingStep>
    )
}

OnboardingErrorTrackingSourceMapsStep.stepKey = OnboardingStepKey.SOURCE_MAPS
