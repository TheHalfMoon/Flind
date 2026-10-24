# Wave 37 — Correct MCP OAuth installation completion and callback validation

## Bug confirmed in source

Both installTemplateWithOAuth and installCustomWithOAuth returned the
cancelled outcome even when the native authentication session returned
success. The marketplace install screen treated that outcome as a refusal
and therefore did not refetch installations or navigate back on success.

The custom-server install screen ignored cancellation and navigated back
unconditionally. The optional callback listener trusted any URL beginning
with the registered callback prefix, including lookalike paths.

## Fix

1. Introduce a strict, shared callback predicate for the registered Flind
   URL scheme, exact mcp-oauth host and callback path, with no error query.
2. Count an Expo WebBrowser success only when the returned URL satisfies
   that predicate, rather than trusting the success flag alone.
3. Return completed from both install helpers after actual successful
   callback, preserving cancelled on dismissal or unexpected/error links.
4. In the custom installer, do not refetch or navigate after cancellation;
   restore the submission control so the user can retry.
5. Reuse callback validation for listeners and reauthorization.
6. Keep the external OAuth install_source protocol value unchanged.

## Evidence

- 18 native Vitest behavioral cases cover exact callback validation,
  benign and malicious callback URLs, direct install response, successful
  and dismissed OAuth for both custom/template flows, reauthorization,
  install request contracts and backend failure propagation.
- Full Mobile Vitest 76 suites: **738/738 PASS**; Mobile Studio 15 suites:
  **224/224 PASS**. Combined **962/962 PASS**.
- Mobile and Mobile Studio TypeScript: PASS, Mobile baseline empty.
- Full Flind Python source regressions: **294/294 PASS**.
- Local two-client qualification runner: PASS, and diff/source formatting
  checks PASS.
- No real OAuth token exchange, callback server, device or account was
  contacted by tests.

## Remaining release gates

Browser mock tests do not establish actual Expo WebBrowser, iOS native
session, Android Custom Tabs or provider redirect behavior. Device
E2E and backend installation persistence/refetch remain unqualified.
No publication or deployment. Keep the GitHub repository private,
inherited Actions disabled and required legal attribution preserved.
