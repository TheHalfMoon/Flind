import { flindDocsUrl } from 'lib/flindPublicLinks'
import { ICONS } from 'lib/integrations/utils'

import { GitLabIntegration } from '../components/Integrations'
import { defineIntegration } from '../integrationDefinition'

export const GitLab = defineIntegration(
    {
        slug: 'gitlab',
        kind: 'gitlab',
        name: 'GitLab',
        logo: ICONS.gitlab,
        subtitle: 'Connect your GitLab projects to Flind',
        description: 'Connect GitLab to create and link issues directly from Flind error tracking and replays.',
        capabilities: [
            'Create GitLab issues from error tracking',
            'Link existing GitLab issues to Flind',
            'Keep engineering work connected to product signals',
        ],
        docsUrl: flindDocsUrl('error-tracking/integrations') ?? undefined,
    },
    GitLabIntegration
)
