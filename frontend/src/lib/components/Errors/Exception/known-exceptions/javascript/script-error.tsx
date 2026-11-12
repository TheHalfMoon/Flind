import { defineKnownException } from '../registry'
import { KnownExceptionBanner } from './base'

defineKnownException({
    match(exception) {
        return exception.value.startsWith('Script error') && exception.type === 'Error'
    },
    render() {
        return (
            <KnownExceptionBanner>
                This error occurs when JavaScript exceptions are thrown from a third-party script but details are hidden
                due to cross-origin restrictions. Confirm the script is served with the required cross-origin headers if
                you need the browser to expose full error details.
            </KnownExceptionBanner>
        )
    },
})
