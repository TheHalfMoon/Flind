import { openSupportOptions } from 'lib/lemon-ui/LemonToast/getHelp'
import { preflightLogic } from 'lib/logic/preflightLogic'

import { sidePanelStateLogic } from '~/layout/navigation-3000/sidepanel/sidePanelStateLogic'
import { SidePanelTab } from '~/types'

/**
 * Opens support where the person already is, for any "contact support" trigger.
 *
 * In-app support uses the side panel when it is available and supported by this instance.
 * Login, onboarding, and self-hosted contexts without that panel may only open an
 * explicitly configured Flind documentation URL; when none exists, no remote
 * support request is made. The campaign tag is encoded before navigation.
 */
export function openInAppSupport(utmCampaign?: string): void {
    const isCloudOrDev = preflightLogic.findMounted()?.values.isCloudOrDev
    const sidePanelAvailable = sidePanelStateLogic.findMounted()?.values.sidePanelAvailable
    if (!isCloudOrDev || !sidePanelAvailable) {
        openSupportOptions(utmCampaign)
        return
    }

    // openSidePanel is the same action every other in-app support entry point calls. It writes the
    // `#panel=support` hash with `replace`, so Back leaves in one press instead of stranding an open
    // panel. The side panel displays the Flind support options configured for this instance.
    sidePanelStateLogic.actions.openSidePanel(SidePanelTab.Support)
}
