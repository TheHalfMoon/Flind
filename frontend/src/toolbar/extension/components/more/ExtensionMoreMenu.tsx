import { LemonDivider } from 'lib/lemon-ui/LemonDivider'

import { ExtensionDebugInfo } from './ExtensionDebugInfo'
import { ExtensionPiiMasking } from './ExtensionPiiMasking'
import { ExtensionScreenshotForEvent } from './ExtensionScreenshotForEvent'

export function ExtensionMoreMenu(): JSX.Element {
    return (
        <div className="flex flex-col gap-3">
            <ExtensionDebugInfo />
            <LemonDivider className="my-0" />
            <ExtensionPiiMasking />
            <LemonDivider className="my-0" />
            <ExtensionScreenshotForEvent />
        </div>
    )
}
