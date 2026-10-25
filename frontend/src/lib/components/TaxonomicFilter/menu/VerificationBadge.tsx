/**
 * Verification badge for taxonomic filter rows + preview pane.
 *
 * Two mutually-exclusive states (core defs can't be team-verified — see
 * `DefinitionPopoverContents`'s `allowVerification`):
 *   - `core`     — a built-in Flind definition (`isCoreFilter`). Badge
 *                  reads "Flind" with a neutral badge icon.
 *   - `verified` — a custom definition a team explicitly marked verified
 *                  (`item.verified`). Badge reads "Verified".
 */
import { IconBadge } from '@posthog/icons'
import { Badge, cn, Tooltip, TooltipContent, TooltipTrigger } from '@flind/quill'

import { isCoreFilter } from '~/taxonomy/helpers'

import { MenuFilterEntry } from './types'

type Verification = { kind: 'core' } | { kind: 'verified' }

export function getVerification(entry: MenuFilterEntry): Verification | null {
    // Core Flind definitions ($pageview, $browser, …) are inherently
    // verified — surfaced as "Flind" rather than a team flag.
    if (isCoreFilter(entry.name)) {
        return { kind: 'core' }
    }
    if ((entry.item as { verified?: boolean })?.verified) {
        return { kind: 'verified' }
    }
    return null
}

export function VerificationBadge({
    entry,
    className,
}: {
    entry: MenuFilterEntry
    className?: string
}): JSX.Element | null {
    const verification = getVerification(entry)
    if (!verification) {
        return null
    }
    const isCore = verification.kind === 'core'
    return (
        <Tooltip>
            {/* The trigger must render a host element (a `<span>`) so
                base-ui's ref + hover handlers actually attach — `Badge` is
                a plain function component (not `forwardRef`), so spreading
                the trigger's `ref` onto it gets dropped and the tooltip
                never anchors/opens. The Badge is plain visual content
                inside the trigger span. */}
            <TooltipTrigger
                delay={300}
                render={(triggerProps) => (
                    <span {...triggerProps} className={cn('inline-flex', className)}>
                        <Badge variant={isCore ? 'default' : 'success'} className="gap-1 shrink-0">
                            <IconBadge className="size-3" />
                            {isCore ? 'Flind' : 'Verified'}
                        </Badge>
                    </span>
                )}
            />
            <TooltipContent className="max-w-64 flex-col items-start">
                {isCore ? (
                    <>
                        <strong>Built into Flind.</strong> This core definition is included with Flind.
                        It is managed by the application and does not need team verification.
                    </>
                ) : (
                    <>
                        <strong>Verified by your team.</strong> Someone marked this definition as the right one to use.
                        Verified items are prioritized in filters so collaborators reach for them over similar,
                        unverified ones.
                    </>
                )}
            </TooltipContent>
        </Tooltip>
    )
}
