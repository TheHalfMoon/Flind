import { Link } from '@flind/lemon-ui'

import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'
import { extractReactErrorCode } from './react-minified-error-code'

defineKnownException({
    match(exception) {
        return extractReactErrorCode(exception.value) !== null
    },
    render(exception) {
        const errorCode = extractReactErrorCode(exception.value)
        return (
            <KnownExceptionBanner>
                React shortens error messages in production builds.{' '}
                {errorCode && (
                    <Link to={'https://react.dev/errors/' + errorCode} target="_blank">
                        Decode this error in the official React documentation
                    </Link>
                )}
                {errorCode ? '. ' : ''}
                Reproduce the issue with a development build to inspect a full error message and useful stack trace.
            </KnownExceptionBanner>
        )
    },
})
