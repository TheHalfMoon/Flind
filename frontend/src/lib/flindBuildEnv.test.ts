import fs from 'fs'
import path from 'path'

import { flindBuildEnv } from './flindBuildEnv'

// Modules that read Flind deployment settings. They must stay loadable by Node-based tools
// (Jest, Playwright), so they read flindBuildEnv instead of Vite's `import.meta.env`.
const FLIND_CONFIG_MODULES = [
    'lib/flindPublicLinks.ts',
    'lib/flindSupportMailto.ts',
    'lib/flindRegionHosts.ts',
    'lib/oauth/oauthClient.ts',
    'lib/components/HelpMenu/incidentStatus.ts',
    'scenes/authentication/shared/arrivedFromWebsiteLogic.ts',
]

describe('flindBuildEnv', () => {
    it('fails closed when no build-time values are injected', () => {
        expect(flindBuildEnv).toEqual({})
        expect(flindBuildEnv.VITE_FLIND_DOCS_URL).toBeUndefined()
        expect(flindBuildEnv.VITE_FLIND_OAUTH_US_CLIENT_ID).toBeUndefined()
    })

    it.each(FLIND_CONFIG_MODULES)('%s reads settings without import.meta', (relativePath) => {
        const source = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8')

        expect(source).not.toMatch(/import\.meta/)
        expect(source).toMatch(/from 'lib\/flindBuildEnv'/)
    })
})
