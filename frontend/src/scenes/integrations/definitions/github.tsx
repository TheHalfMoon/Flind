import { Link } from '@flind/lemon-ui'

import { flindDocsUrl } from 'lib/flindPublicLinks'
import { ICONS } from 'lib/integrations/utils'
import { urls } from 'scenes/urls'

import { GithubIntegration } from '../components/Integrations'
import { defineIntegration } from '../integrationDefinition'

export const GitHub = defineIntegration(
    {
        slug: 'github',
        kind: 'github',
        name: 'GitHub',
        logo: ICONS.github,
        subtitle: 'Link code, track issues, and let Flind ship pull requests',
        description: (
            <>
                Connect GitHub to link issues and pull requests with Flind and create issues directly from error
                tracking. With <Link to={urls.integration('slack')}>Slack</Link> and{' '}
                Flind Desktop connected, tag @Flind to draft pull requests and ship code changes straight to your repositories.
            </>
        ),
        capabilities: [
            'Let @Flind draft pull requests and ship code changes',
            'Create GitHub issues from error tracking',
            'Link pull requests and issues to Flind',
            'Attribute code changes across your repositories',
        ],
        docsUrl: flindDocsUrl('libraries/github') ?? undefined,
    },
    GithubIntegration
)
