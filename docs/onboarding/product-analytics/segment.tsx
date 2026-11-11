import { OnboardingComponentsContext, createInstallation } from 'scenes/onboarding/shared/OnboardingDocsContentWrapper'

import { StepDefinition } from '../steps'

export const getSegmentSteps = (ctx: OnboardingComponentsContext): StepDefinition[] => {
    const { CodeBlock, Markdown, CalloutBox, dedent } = ctx

    return [
        {
            title: 'Add Flind destination',
            badge: 'required',
            content: (
                <Markdown>
                    Segment is a customer data platform that can route your analytics data to Flind and other
                    destinations. In your Segment workspace, go to **Connections** &gt; **Catalog** and search for
                    **Flind**. Click **Add Destination** and select the source you want to connect.
                </Markdown>
            ),
        },
        {
            title: 'Enter your credentials',
            badge: 'required',
            content: (
                <>
                    <Markdown>Enter your Flind project token:</Markdown>
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
            title: 'Verify the connection',
            badge: 'recommended',
            content: (
                <>
                    <Markdown>
                        Segment will now forward `track`, `identify`, `page`, and `group` calls to Flind.
                    </Markdown>
                    <CalloutBox type="fyi" title="Learn more">
                        <Markdown>
                            See the [Segment integration docs](https://posthog.com/docs/libraries/segment) for more
                            details.
                        </Markdown>
                    </CalloutBox>
                </>
            ),
        },
    ]
}

export const SegmentInstallation = createInstallation(getSegmentSteps)
