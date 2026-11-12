import { Link } from '@flind/lemon-ui'

import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return !!exception.value.match(/React(?:\.js)?(?: DOM)?(?: production)? error #(\d+)/i)
    },
    render(exception) {
        const errorCode = exception.value.match(/React(?:\.js)?(?: DOM)?(?: production)? error #(\d+)/i)?.[1]
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
