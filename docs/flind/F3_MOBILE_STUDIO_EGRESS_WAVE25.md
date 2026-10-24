# F3 Wave 25 — Flind Mobile Studio OAuth and MCP boundary

## Observed inherited behavior

The second mobile application (@flind/mobile-studio) hardcoded the original
cloud service's US/EU OAuth origins and public OAuth client registrations,
plus third-party MCP endpoints per region. A cached OAuth session could retain
an inherited cloud host even after changing application defaults. MCP clients
attach a bearer token to outbound requests.

## Changes

- Replace regional hosted API origins, OAuth client IDs, and MCP server URLs
  with explicit Flind Expo build-time configuration and origin/path validation.
- Deny inherited upstream cloud names (including trailing DNS root dots),
  external HTTP, URL-embedded credentials, query parameters, fragments, and
  non-API/MCP paths.
- Allow optional local loopback HTTP for self-hosted development only; hosted
  regions are disabled until explicitly configured.
- Fail closed on absent or malformed OAuth client registrations.
- Disable redirect following for OAuth token exchange and MCP streamable HTTP
  transport (redirect: error).
- Reject stale persisted sessions when the stored host does not exactly match
  the configured approved destination, even when OAuth scope version matches.
  The guard also prevents tokens already held in memory from being used if
  configuration changes.
- Rename the local-only host constant to FLIND_LOCAL_HOST. The seeded local
  dev identity (test@posthog.com), the native posthog:// callback scheme,
  and existing wire-protocol MCP consumer keys are left intact pending
  coordinated backend/native migration; they are not cleared release gates.

## Configuration

Use products/desktop/apps/mobilehog/.env.example for:
- EXPO_PUBLIC_FLIND_STUDIO_US_URL and EXPO_PUBLIC_FLIND_STUDIO_EU_URL
- EXPO_PUBLIC_FLIND_STUDIO_OAUTH_US_CLIENT_ID and EU_CLIENT_ID
- EXPO_PUBLIC_FLIND_STUDIO_MCP_US_URL and MCP_EU_URL
- Optional EXPO_PUBLIC_FLIND_STUDIO_MCP_LOCAL_URL for local development

No hosted Flind instance or client registration was created.

## Qualification

- Dependency-free runtime behavior checks execute the transpiled actual
  TypeScript config implementation: 16/16 PASS (offline defaults,
  explicit TLS/loopback, inherited cloud denial, URL credential and path
  rejection, OAuth registration requirements).
- All modified TypeScript files and new test files parsed with zero syntax errors.
- Python regressions protect call graph and stale-token gate.
- Full Flind Python suite: 250/250 PASS after the complete edit.
- Native/Expo/Vitest end-to-end authentication remains NOT QUALIFIED:
  mobile-studio dependencies are not installed in the lightweight Mac
  checkout, so its new Vitest tests have not executed.
- No complete native credential redirect trace, mobile task replay, SDK
  integration, push notifications, filesystem migration or installed iOS
  app validation has been conducted.

RELEASE REMAINS NO-GO. Keep GitHub private, inherited GitHub Actions
disabled, no public release, no deployment. Preserve mandatory attribution.
