# Wave 35 — Portable session event types and MCP mobile host correctness

## What was actually broken

Flind Mobile maintained separate declarations for session events and notification
attachments but consumed the portable event stream emitted by Desktop Core.
Missing SessionEvent, SessionNotification and CloudArtifactRef exports led to
repeated compiler failures in the session store, viewer and prompt attachment
recovery. A cloud-attachment reference was generated at runtime but missing
from the mobile attachment interface.

React Native screens used the non-existent StyleSheet.absoluteFillObject field
instead of the exported absoluteFill constant. The MCP mobile app-host UI
referenced parser output fields serverName/toolName when the canonical parser
returns server/tool, and its CSP type was wider than the type accepted by
the mobile MCP AppBridge. A React test renderer used a mocked native tag
in a manner TypeScript could not typecheck, and a repository option test
provided incomplete integration fixtures.

## Corrections

- Export SessionEvent and SessionNotification aliases directly from
  Core's PortableSessionEvent/PortableSessionNotification types; re-use the
  CloudArtifactRef type from Core's prompt-content contract.
- Declare cloudArtifact in the mobile attachment interface rather than
  treating the existing runtime value as an excess undocumented property.
- Use StyleSheet.absoluteFill on three screens; preserve layout behavior.
- Read parsed MCP fields server/tool. Match the AppBridge CSP contract with
  McpUiResourceCsp, preserving CSP validation.
- Use the existing mocked React test renderer helper and explicitly select
  QuestionCard in the component test; complete GitHub integration fixtures
  with required fields.
- Shrink the Mobile TypeScript baseline with the original --prune operation,
  rather than regenerating it or adding suppressions.

## Evidence

- Raw Mobile tsc diagnostic count: 37 before, **14 after**. No new errors
  after pruning; TypeScript baseline guard passes. Remaining 14 are real.
- Three additional source regressions cover portable types, MCP identifier
  mapping and React Native style constants.
- Both-app original Vitest regression on macbook: Mobile 719/719, Mobile Studio
  224/224, **943/943 combined PASS**.
- Flind full Python source regression suite: **287/287 PASS**.
- Local both-mobile qualifier: PASS (both TypeScript gates and both Vitest suites).

## Explicit limitations

This is local code-path/type regression work, not native iOS/Android runtime
qualification. There is no proof of end-to-end session replay or MCP WebView
sandbox execution on devices. The inherited 14 Mobile TypeScript diagnostics,
back-end and ClickHouse integration, security/egress audits and wider brand
identity gates still block release. No publication, public deployment or
paid model service was involved. The repo remains private with inherited
GitHub Actions disabled. Required legal attribution is preserved.
