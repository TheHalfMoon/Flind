export * from '../exports';
import type { PostHogFetchBodyBytes } from '@flind/core';
import { PostHogBackendClient } from '../client';
import { ErrorTracking as CoreErrorTracking } from '@flind/core';
import type { SpanContextManager } from '@flind/core';
import { PostHogContext } from '../extensions/context/context';
export declare class PostHog extends PostHogBackendClient {
    getLibraryId(): string;
    protected compressPayload(payload: string): Promise<PostHogFetchBodyBytes | null>;
    protected initializeContext(): PostHogContext;
    protected initializeSpanContextManager(): SpanContextManager;
    protected hostResourceAttributes(): Record<string, string>;
    protected createErrorPropertiesBuilder(): CoreErrorTracking.ErrorPropertiesBuilder;
}
//# sourceMappingURL=index.node.d.ts.map