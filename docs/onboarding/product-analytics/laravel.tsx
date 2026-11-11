import { OnboardingComponentsContext, createInstallation } from 'scenes/onboarding/shared/OnboardingDocsContentWrapper'

import { StepDefinition } from '../steps'

export const getLaravelInstallSteps = (ctx: OnboardingComponentsContext): StepDefinition[] => {
    const { CodeBlock, Markdown, dedent } = ctx

    return [
        {
            title: 'Install the package',
            badge: 'required',
            content: (
                <>
                    <Markdown>Install the Flind PHP library using Composer:</Markdown>
                    <CodeBlock
                        blocks={[
                            {
                                language: 'bash',
                                file: 'Terminal',
                                code: dedent`
                                composer require posthog/posthog-php
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
                    <Markdown>
                        Initialize Flind in the `boot` method of `app/Providers/AppServiceProvider.php`:
                    </Markdown>
                    <CodeBlock
                        blocks={[
                            {
                                language: 'php',
                                file: 'app/Providers/AppServiceProvider.php',
                                code: dedent`
                                <?php

                                namespace App\\Providers;

                                use Illuminate\\Support\\ServiceProvider;
                                use Flind\\Flind;

                                class AppServiceProvider extends ServiceProvider
                                {
                                    public function boot(): void
                                    {
                                        Flind::init(
                                            '<ph_project_token>',
                                            [
                                                'host' => '<ph_client_api_host>'
                                            ]
                                        );
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

export const getLaravelEventStep = (ctx: OnboardingComponentsContext): StepDefinition => {
    const { CodeBlock, Markdown, dedent } = ctx

    return {
        title: 'Send events',
        badge: 'optional',
        content: (
            <>
                <Markdown>Capture custom events using the Flind client:</Markdown>
                <CodeBlock
                    blocks={[
                        {
                            language: 'php',
                            file: 'PHP',
                            code: dedent`
                                Flind::capture([
                                    'distinctId' => 'test-user',
                                    'event' => 'test-event',
                                ]);
                            `,
                        },
                    ]}
                />
            </>
        ),
    }
}

export const getLaravelSteps = (ctx: OnboardingComponentsContext): StepDefinition[] => [
    ...getLaravelInstallSteps(ctx),
    getLaravelEventStep(ctx),
]

export const LaravelInstallation = createInstallation(getLaravelSteps)
