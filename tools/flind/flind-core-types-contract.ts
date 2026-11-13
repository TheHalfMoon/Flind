// Public type surface of the private Flind core and types SDKs.
// This module has no runtime behavior; tsc validates re-export resolution.
import type {
    ExceptionRateLimiterConfig,
    Properties,
    SpanRecord,
    BeforeSpanSendFn,
} from '@flind/core'
import type {
    PostHogConfig,
    CaptureOptions,
    FeatureFlagOptions,
    JsonRecord,
} from '@flind/types'

export type FlindCoreTypesConsumer = {
    configuration: PostHogConfig
    collectorProperties: Properties
    logPayload: JsonRecord
    captureOptions: CaptureOptions
    featureFlagOptions: FeatureFlagOptions
    exceptionConfig: ExceptionRateLimiterConfig
    span: SpanRecord
    spanFilter: BeforeSpanSendFn
}
