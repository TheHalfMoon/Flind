import { OnboardingComponentsContext, createInstallation } from 'scenes/onboarding/shared/OnboardingDocsContentWrapper'

import { StepDefinition } from '../steps'

export const getAndroidInstallSteps = (ctx: OnboardingComponentsContext): StepDefinition[] => {
    const { CodeBlock, Markdown, dedent } = ctx

    return [
        {
            title: 'Install the dependency',
            badge: 'required',
            content: (
                <>
                    <Markdown>Add the Flind Android SDK to your `build.gradle` dependencies:</Markdown>
                    <CodeBlock
                        blocks={[
                            {
                                language: 'kotlin',
                                file: 'build.gradle',
                                code: dedent`
                                    dependencies {
                                        implementation("com.posthog:posthog-android:3.+")
                                    }
                                `,
                            },
                        ]}
                    />
                </>
            ),
        },
        {
            title: 'Configure Flind',
            badge: 'required',
            content: (
                <>
                    <Markdown>Initialize Flind in your Application class:</Markdown>
                    <CodeBlock
                        blocks={[
                            {
                                language: 'kotlin',
                                file: 'SampleApp.kt',
                                code: dedent`
                                    class SampleApp : Application() {

                                        companion object {
                                            const val POSTHOG_PROJECT_TOKEN = "<ph_project_token>"
                                            const val POSTHOG_HOST = "<ph_client_api_host>"
                                        }

                                        override fun onCreate() {
                                            super.onCreate()

                                            // Create a Flind Config with the given project token and host
                                            val config = PostHogAndroidConfig(
                                                apiKey = POSTHOG_PROJECT_TOKEN,
                                                host = POSTHOG_HOST
                                            )

                                            // Setup Flind with the given Context and Config
                                            PostHogAndroid.setup(this, config)
                                        }
                                    }
                                `,
                            },
                        ]}
                    />
                </>
            ),
        },
    ]
}

export const getAndroidEventStep = (ctx: OnboardingComponentsContext): StepDefinition => {
    const { CodeBlock, Markdown, dedent } = ctx

    return {
        title: 'Send events',
        badge: 'recommended',
        content: (
            <>
                <Markdown>
                    Once installed, Flind will automatically start capturing events. You can also manually send events
                    to test your integration:
                </Markdown>
                <CodeBlock
                    blocks={[
                        {
                            language: 'kotlin',
                            file: 'Kotlin',
                            code: dedent`
                                    import com.posthog.PostHog

                                    Flind.capture(
                                        event = "button_clicked",
                                        properties = mapOf(
                                            "button_name" to "signup"
                                        )
                                    )
                                `,
                        },
                    ]}
                />
            </>
        ),
    }
}

export const getAndroidSteps = (ctx: OnboardingComponentsContext): StepDefinition[] => [
    ...getAndroidInstallSteps(ctx),
    getAndroidEventStep(ctx),
]

export const AndroidInstallation = createInstallation(getAndroidSteps)
