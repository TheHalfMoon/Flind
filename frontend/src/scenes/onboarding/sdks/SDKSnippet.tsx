import { isOwnedFlindDocsDestination } from 'lib/flindPublicLinks'
import { Link } from 'lib/lemon-ui/Link'

import { SDK } from '~/types'

interface SDKSnippetProps {
    sdk: SDK
    sdkInstructions: () => JSX.Element
}

export const SDKSnippet = ({ sdk, sdkInstructions }: SDKSnippetProps): JSX.Element => {
    return (
        <div>
            <div className="mb-8">
                <h3 className="text-xl font-bold mb-2">Send {sdk.name} data to Flind using the integration SDK</h3>
                {isOwnedFlindDocsDestination(sdk.docsLink) ? (
                    <Link className="" to={sdk.docsLink} target="_blank" targetBlankIcon>
                        Read the Flind SDK documentation
                    </Link>
                ) : (
                    <p className="text-muted text-sm">SDK documentation is not configured for this Flind instance.</p>
                )}
            </div>
            <div className="deprecated-space-y-4">{sdkInstructions()}</div>
        </div>
    )
}
