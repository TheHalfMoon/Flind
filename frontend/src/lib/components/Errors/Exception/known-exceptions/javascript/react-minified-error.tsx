import { Link } from '@flind/lemon-ui'

import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return !!exception.value.match(/React(?:\.js)?(?: DOM)?(?: production)? error #(\d+)/i)
    },
    render(exception) {
        const errorCode = exception.value.match(/React(?:\.js)?(?: DOM)?(?: production)? error #(\d+)/i)
        return (
            <KnownExceptionBanner>
                React minifies error messages as part of its production build process to reduce bundle size, and does
                not include a stack trace. You can visit the{' '}
                <Link to={`https://react.dev/errors/${errorCode}`} target="_blank">
                    React docs
                </Link>{' '}
                to see the full description. Reproduce the issue in a development build to get a readable stack trace.
            </KnownExceptionBanner>
        )
    },
})
