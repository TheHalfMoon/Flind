# @flind/react

Flind's in-repository React SDK compatibility package. Vendored from the MIT-licensed React integration published at version 1.11.3; see NOTICE.md and LICENSE.

This is **not published**. The original public React API symbol names (such as `PostHogErrorBoundary`) and the `posthog-js` peer dependency are retained temporarily for source/binary compatibility. This does **not** make the underlying browser SDK Flind-native or its data ingestion independently qualified. Migrate code symbols and the browser SDK together in a later tested stage.

Entry points: ESM `dist/esm/index.js`, CommonJS `dist/umd/index.js`, types `dist/types/index.d.ts`, and `slim` / `surveys` subpath directories. Do not ship or publish without complete SDK security, privacy and ingestion tests.
