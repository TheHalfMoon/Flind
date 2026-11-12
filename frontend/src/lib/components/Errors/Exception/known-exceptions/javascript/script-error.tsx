import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return exception.value.startsWith('Script error') && exception.type === 'Error'
    },
    render() {
        return (
            <KnownExceptionBanner>
                Browsers can hide details of exceptions thrown in cross-origin scripts. Check the browser console and
                configure the script's <code>crossorigin="anonymous"</code> attribute together with appropriate CORS
                response headers, or serve the script from the same origin, to make stack details available.
            </KnownExceptionBanner>
        )
    },
})
