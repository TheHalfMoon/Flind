# Wave 34 — Mobile TypeScript baseline 44 to 37

## Problem: real mobile type errors were already known

The original Flind Mobile TypeScript guard reported 44 inherited errors
as an explicit grandfathered baseline. Reviewing actual tsc output revealed
a runtime-invalid import in the DiffBlock visual component and a structurally
incompatible optional transport-check helper.

## Changes

- Correct the DiffBlock import to use the Mobile inbox activityLog module,
  which actually exports parseDiffLines and already has behavioral tests.
  The old target, @flind/core/inbox/activityLog, does not export it.
  This fixes three TypeScript diagnostics and a potential runtime import error.
- Change isStdioMcpServer to accept unknown and safely test the optional
  transport_type at runtime after object/null/property checks. The generated
  API DTOs do not declare this optional compatibility property; this safe
  structural check preserves behavior while removing four type errors.
- Add eleven Vitest cases for missing, malformed and recognized transports.
- Prune only the seven actually resolved diagnostics using the existing
  mobile typecheck --prune command. Do not raise or regenerate the baseline,
  do not introduce any cast or ignore rules.

## Evidence

- Raw full Mobile tsc diagnostic count: 44 before, 37 after.
- Mobile baseline gate: PASS, zero new errors, 37 inherited errors remain.
- 22 focused Vitest tests passed for native diff parsing and MCP transport.
- Full rerun on macbook (2026-10-24): Mobile 719/719 Vitest PASS;
  Mobile Studio 224/224 Vitest PASS; combined 943/943 PASS. Studio
  TypeScript clean; Mobile baseline gate PASS (37 inherited errors).
  Full Flind Python source regressions: 284/284 PASS.

## Remaining work

The 37 real TypeScript diagnostics are not fixed by this wave. This is not
a clean full-Mobile TypeScript pass or a release qualification. Native device,
backend, SDK, ingestion, egress, and identity gates remain NO-GO.

No deploy or publishing; repo private; inherited Actions disabled. Preserve
required legal notices and external package provenance.
