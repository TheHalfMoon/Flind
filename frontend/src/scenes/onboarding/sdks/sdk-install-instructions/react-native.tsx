import { useValues } from 'kea'

import { Link } from '@flind/lemon-ui'

import { CodeSnippet, Language } from 'lib/components/CodeSnippet'
import { flindDocsSectionUrl } from 'lib/flindPublicLinks'
import { apiHostOrigin } from 'lib/utils/apiHost'
import SetupWizardBanner from 'scenes/onboarding/shared/SetupWizardBanner'
import { teamLogic } from 'scenes/teamLogic'

export interface RNSetupProps {
    hideWizard?: boolean
    includeReplay?: boolean
    includeSurveys?: boolean
}

function RNInstallSnippet({ includeReplay, includeSurveys }: RNSetupProps): JSX.Element {
    return (
        <CodeSnippet language={Language.Bash}>
            {`# Expo apps
npx expo install posthog-react-native expo-file-system expo-application expo-device expo-localization${
                includeReplay ? ` posthog-react-native-session-replay` : ''
            }${includeSurveys ? ` react-native-safe-area-context react-native-svg` : ''}

# Standard React Native apps
yarn add posthog-react-native @react-native-async-storage/async-storage react-native-device-info react-native-localize${
                includeReplay ? ` posthog-react-native-session-replay` : ''
            }${includeSurveys ? ` react-native-safe-area-context react-native-svg` : ''}
# or
npm i -s posthog-react-native @react-native-async-storage/async-storage react-native-device-info react-native-localize${
                includeReplay ? ` posthog-react-native-session-replay` : ''
            }${includeSurveys ? ` react-native-safe-area-context react-native-svg` : ''}

# for iOS
cd ios
pod install`}
        </CodeSnippet>
    )
}

function RNSetupSnippet({ includeReplay }: RNSetupProps): JSX.Element {
    const { currentTeam } = useValues(teamLogic)
    const url = apiHostOrigin()
    const directSetupDocs = flindDocsSectionUrl('libraries/react-native', 'without-the-posthogprovider')

    return (
        <>
            <p>
                Flind is most easily used via the <code>PostHogProvider</code> component but if you need to
                instantiate it directly,{' '}
                {directSetupDocs ? (
                    <Link to={directSetupDocs}>read the Flind setup documentation</Link>
                ) : (
                    'consult the React Native configuration guidance for your Flind instance'
                )}
                .
            </p>
            <CodeSnippet language={Language.JSX}>
                {`// App.(js|ts)
import { PostHogProvider } from 'posthog-react-native'
...

export function MyApp() {
    return (
        <PostHogProvider apiKey="${currentTeam?.api_token ?? 'YOUR_PROJECT_API_KEY'}" options={{
            host: "${url}",
            ${
                includeReplay
                    ? `
            // Review your Flind instance's replay setup and privacy settings
            // before enabling session recording in production.
            enableSessionReplay: true,
            sessionReplayConfig: {
                // Whether text inputs are masked. Default is true.
                // Password inputs are always masked regardless
                maskAllTextInputs: true,
                // Whether images are masked. Default is true.
                maskAllImages: true,
                // Opt in to native Logcat capture only after a project privacy review.
                // This copyable Flind setup keeps it disabled by default.
                // The Flind replay settings may support remote configuration.
                captureLog: false,
                // Opt in to iOS network timing, size and status metadata only
                // after privacy review; request/response bodies are not captured.
                // Keep network metadata collection disabled in the sample.
                captureNetworkTelemetry: false,
                // Throttling delay used to reduce the number of snapshots captured and reduce performance impact
                // The lower the number more snapshots will be captured but higher the performance impact
                // Default is 1000ms
                throttleDelayMs: 1000,
            },`
                    : ''
            }
        }}>
            <RestOfApp />
        </PostHogProvider>
    )
}`}
            </CodeSnippet>
        </>
    )
}

function RNSetupSurveysProvider(): JSX.Element {
    return (
        <>
            <p>
                Add PostHogSurveyProvider to your app anywhere inside PostHogProvider. This component fetches surveys.
                It also acts as the root for where popover surveys are rendered.
            </p>
            <CodeSnippet language={Language.JSX}>
                {`<PostHogProvider>
    <PostHogSurveyProvider>{children}</PostHogSurveyProvider>
</PostHogProvider>`}
            </CodeSnippet>
            <p>
                If you're not using the PostHogProvider, add PostHogSurveyProvider to your app anywhere inside your app
                root component.
            </p>
            <CodeSnippet language={Language.JSX}>
                {`<YourAppRoot>
  <PostHogSurveyProvider>{children}</PostHogSurveyProvider>
</YourAppRoot>`}
            </CodeSnippet>
            <p>You can also pass your client instance to the PostHogSurveyProvider.</p>
            <CodeSnippet
                language={Language.JSX}
            >{`<PostHogSurveyProvider client={posthog}>{children}</PostHogSurveyProvider>`}</CodeSnippet>
        </>
    )
}

export function SDKInstallRNInstructions(props: RNSetupProps): JSX.Element {
    return (
        <>
            <SetupWizardBanner integrationName="React Native" hide={props.hideWizard} />
            <h3>Install</h3>
            <RNInstallSnippet includeReplay={props.includeReplay} includeSurveys={props.includeSurveys} />
            <h3>Configure</h3>
            <RNSetupSnippet includeReplay={props.includeReplay} />
            {props.includeSurveys && (
                <>
                    <h3>Setup SurveysProvider</h3>
                    <RNSetupSurveysProvider />
                </>
            )}
        </>
    )
}
