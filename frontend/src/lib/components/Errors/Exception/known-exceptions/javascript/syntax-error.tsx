import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return exception.type === 'SyntaxError'
    },
    render() {
        return (
            <KnownExceptionBanner>
                JavaScript failed to parse code at this location. Check the browser console for the file and line
                number, review syntax and build/transpilation output, and ensure the correct source maps are available
                to this Flind deployment.
            </KnownExceptionBanner>
        )
    },
})
