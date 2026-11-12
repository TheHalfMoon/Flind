import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return exception.value?.startsWith('Non-Error promise rejection') ?? false
    },
    render() {
        return (
            <KnownExceptionBanner>
                This issue occurs when a promise is rejected with a string or object rather than an Error. The
                rejection may lack a useful stack trace. Reject an Error instance (for example,
                <code> Promise.reject(new Error(message))</code>) and preserve its cause to capture more context.
            </KnownExceptionBanner>
        )
    },
})
