import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return exception.value?.startsWith('Non-Error promise rejection') ?? false
    },
    render() {
        return (
            <KnownExceptionBanner>
                This issue occurs when non Error objects are provided to Promise rejections. When you do this a stack
                trace is not captured as part of the caught exception. Reject with an Error instance so the stack trace
                and message can be recorded.
            </KnownExceptionBanner>
        )
    },
})
