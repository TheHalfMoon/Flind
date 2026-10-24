# Wave 36 — Mobile TypeScript reaches zero; UI and API contracts converge

## Concrete bugs fixed

1. The API client only accepts MCP install_source posthog or posthog-code.
   The mobile wrappers had accidentally advertised a third, unsupported
   posthog-mobile value. Correct the two type declarations without changing
   the existing OAuth callback scheme. These source values are compatibility.

2. The custom MCP server UI presented auth_type none, which the generated
   install_custom API enum does not permit. Align choices to API key and
   OAuth, defaulting to OAuth as the existing Desktop flow does.

3. Cloud permission options have forward-compatible string kinds, while
   ACP options use a closed enum. The presentation-only functions accept
   both shapes for metadata and rejection classification. Authorization
   response decisions remain governed by the original ACP contract.
   Unknown strings cannot grant permissions.

4. The shared session activity detector treats stopped as terminal rather
   than continuing to display a running state.

5. The API returns GitHub integration IDs as strings or numbers, but the
   legacy mobile repository picker uses numeric IDs. Normalize only safe,
   positive decimal GitHub IDs. Ignore malformed, UUID, fractional or
   unsafe numbers instead of silently coercing to NaN. User-scoped UUID
   integrations have a distinct existing UI path.

6. The react-native-webview v13.17.0 root declaration intersects mutually
   exclusive iOS, Android and Windows interfaces, giving never for some
   props. The MCP host has a narrowly scoped adapter to the actual iOS /
   Android union, preserving the same runtime import and component.
   Native device testing remains a release prerequisite.

7. Prune the last inherited mobile TypeScript baseline entries using the
   pre-existing typecheck --prune command. Baseline is now empty.

## Validation

- Mobile raw tsc --noEmit: 0 errors; baseline guard: 0 new, 0 inherited.
- Focused behavioral tests cover permission shape, stopped status, and
  GitHub ID normalization.
- Full real Mobile Vitest: **720/720 PASS**, 75 suites.
- Full real Mobile Studio Vitest: **224/224 PASS**, 15 suites.
- Combined mobile Vitest: **944/944 PASS**.
- Core permission/activity regression Vitest: **33/33 PASS**.
- Full Flind Python source suite: **291/291 PASS**.
- Mobile, Mobile Studio, Core and API Client TypeScript: PASS (zero errors).
- Local qualification runner: PASS, with its message corrected to report
  the *actual* empty baseline instead of a stale warning.
- Formatting was limited to touched files.

## Remaining NO-GO gates

Passing TypeScript and unit tests is not a release approval. Remaining
unqualified: installed iOS/Android builds, MCP WebView sandbox and OAuth
callbacks on devices, full Django/Postgres/Redis/ClickHouse integration,
SDK data ingestion/query correctness, end-to-end desktop UX, telemetry
and external-egress tracing, first-party identity audit and packaging.
Published external SDK dependencies and mandatory attribution are kept.
Repository private; inherited GitHub Actions disabled. Nothing deployed
or published.
