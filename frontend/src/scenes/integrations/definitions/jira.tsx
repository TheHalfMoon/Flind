import { ICONS } from 'lib/integrations/utils'

import { JiraIntegration } from '../components/Integrations'
import { defineIntegration } from '../integrationDefinition'

export const Jira = defineIntegration(
    {
        slug: 'jira',
        kind: 'jira',
        name: 'Jira',
        logo: ICONS.jira,
        subtitle: 'Create and link Jira issues from Flind',
        description: 'Connect Jira to create and link issues directly from Flind error tracking and replays.',
        capabilities: [
            'Create Jira issues from error tracking',
            'Link existing Jira issues to Flind',
            'Keep your team in sync across tools',
        ],
        docsUrl: 'https://posthog.com/docs/error-tracking/integrations',
    },
    JiraIntegration
)
