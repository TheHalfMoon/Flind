import { OnboardingComponentsContext, createInstallation } from 'scenes/onboarding/shared/OnboardingDocsContentWrapper'

import { StepDefinition } from '../steps'

export const getZapierSteps = (ctx: OnboardingComponentsContext): StepDefinition[] => {
    const { CodeBlock, Markdown, dedent } = ctx

    return [
        {
            title: 'Connect Flind to Zapier',
            badge: 'required',
            content: (
                <>
                    <Markdown>
                        Zapier lets you connect Flind to thousands of other apps. You can use it to send events to
                        Flind from other services or trigger actions based on Flind events. Go to the [Flind
                        integration page](https://zapier.com/apps/posthog/integrations) on Zapier and click **Connect
                        Flind**. When prompted, enter your Flind project token:
                    </Markdown>
                    <CodeBlock
                        blocks={[
                            {
                                language: 'text',
                                file: 'API Key',
                                code: dedent`
                                <ph_project_token>
                            `,
                            },
                        ]}
                    />
                    <Markdown>Enter your Flind host:</Markdown>
                    <CodeBlock
                        blocks={[
                            {
                                language: 'text',
                                file: 'Host',
                                code: dedent`
                                <ph_client_api_host>
                            `,
                            },
                        ]}
                    />
                </>
            ),
        },
        {
            title: 'Create a Zap',
            badge: 'required',
            content: (
                <>
                    <Markdown>
                        Create a Zap that sends events to Flind using the "Capture Event" action. Events captured via
                        Zapier will appear in Flind just like events from any other source.
                    </Markdown>
                    <Markdown>
                        You can use Zapier to connect CRMs, payment processors, customer support tools, and more to your
                        Flind analytics.
                    </Markdown>
                </>
            ),
        },
    ]
}

export const ZapierInstallation = createInstallation(getZapierSteps)
