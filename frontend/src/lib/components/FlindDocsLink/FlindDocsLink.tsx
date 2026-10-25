import { Link } from '@flind/lemon-ui'
import type { ReactNode } from 'react'

import { flindDocsSectionUrl, flindDocsUrl } from 'lib/flindPublicLinks'

export interface FlindDocsLinkProps {
    path: string
    section?: string
    children: ReactNode
}

/** Text, not an inherited external hyperlink, when Flind has no owned docs URL. */
export function FlindDocsLink({ path, section, children }: FlindDocsLinkProps): JSX.Element {
    const href = section ? flindDocsSectionUrl(path, section) : flindDocsUrl(path)
    if (!href) {
        return <>{children}</>
    }
    return (
        <Link to={href} target="_blank" targetBlankIcon>
            {children}
        </Link>
    )
}
