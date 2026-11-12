# @flind/node

Private, in-repository Flind Node SDK compatibility package, staged from the published `posthog-node` 5.63.2 release.

**Not for publication.** This preserves the source and export ABI of the pinned donor distribution while the client SDK and its wire protocol are migrated. The `@posthog/core` runtime dependency and inherited public symbol names remain for compatibility. This package does **not** yet establish independently owned Flind SDK ingestion, a privacy certification or a production release.

Do not change default telemetry hosts, protocol IDs, analytics flags or user-facing installation guidance without dedicated regression tests. A consuming Flind module is migrated as a smoke only; upgrade/rollback and full SDK migration remain separate gates.

Read LICENSE and NOTICE.md for exact provenance and license information.
