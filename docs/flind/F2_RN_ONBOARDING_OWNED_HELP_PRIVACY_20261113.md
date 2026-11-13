# Flind React Native onboarding: owned help, privacy-first template

Status: **exact-head real Jest/TypeScript/E2E qualification pending**.

## Problems

The React Native integration wizard linked directly to inherited provider
documentation, and the copyable replay configuration embedded multiple
links to a different provider's cloud dashboard. Those links did not
identify a Flind-owned service. The same code also rendered the literal
`undefined` as a project token if the selected team had not loaded.

The optional replay template enabled Android Logcat capture and iOS
network timing/response metadata automatically, in addition to session
replay. Such telemetry is more sensitive than necessary in a generic
copy-and-paste setup and should be a deliberate per-project opt-in.

## Repair

- Use only the existing exact-host HTTPS owner-documentation helper
  `flindDocsSectionUrl('libraries/react-native',
  'without-the-posthogprovider')` for the direct-instantiation help.
  If Flind docs are not configured, show useful plain text with no link.
- Remove inherited provider documentation and provider dashboard URLs from
  the copyable snippet. Keep references to Flind's own privacy settings
  as plain-language instructions, not unsupported invented URLs.
- Use `YOUR_PROJECT_API_KEY` instead of the string `undefined` when a
  team token is absent, while retaining the explicit current Flind
  `apiHostOrigin()` destination.
- Retain `PostHogProvider`, a required class exported by the temporary
  compatibility React Native library. Do not pretend the private Flind
  SDK is a public package or rename unrelated SDK APIs.
- Preserve optional replay and survey setup, user text/image masking,
  and throttle configuration. Keep `captureLog` and
  `captureNetworkTelemetry` **false** in the sample, with comments on
  how to enable these capabilities after a project privacy review.

The app's underlying SDK and server-side behavior are unchanged. These
privacy defaults apply to the presented *sample code only*, not existing
customer deployments or previously saved SDK settings.

## Verification

`node --test frontend/bin/flind-rn-owned-docs.test.mjs` checks
the absence of inherited links, owner-host config, token placeholder,
provider API and privacy-safe example settings. A separate GitHub
workflow runs the source contract, alongside branch-scoped full frontend
Jest, TypeScript and migration/rename checks.

These are *not* evidence of functional iOS/Android builds, native device
OAuth, push notifications, session replay storage, or privacy enforcement.
All remain distinct release blockers. The project is **NO-GO** for
release, tags, SDK distribution or deployment without explicit
`GREEN LIGHT FLIND`. Preserve source licenses and copyright notices.
