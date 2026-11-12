import { EmptyMessage } from 'lib/components/EmptyMessage/EmptyMessage'

import { KnownException } from '../Exception/known-exceptions'
import { ErrorTrackingException } from '../types'

export function EmptyStackTrace({
    exception,
    knownException,
}: {
    exception: ErrorTrackingException
    knownException?: KnownException
}): JSX.Element {
    return (
        <div className="mt-2">
            {knownException?.render(exception) ?? (
                <div className="border-1 rounded">
                    <EmptyMessage
                        title="No stacktrace available"
                        description="Check the SDK error capture configuration and confirm that stack traces are available"
                        size="small"
                    />
                </div>
            )}
        </div>
    )
}
