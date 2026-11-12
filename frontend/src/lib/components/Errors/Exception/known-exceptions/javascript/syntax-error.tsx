import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return exception.type === 'SyntaxError'
    },
    render() {
        return (
            <KnownExceptionBanner>
                A SyntaxError means the JavaScript engine could not parse the script. Check the reported file, line, and
                column, and confirm the deployed bundle matches the source build.
            </KnownExceptionBanner>
        )
    },
})
