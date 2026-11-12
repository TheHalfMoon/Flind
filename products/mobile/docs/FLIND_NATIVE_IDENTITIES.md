# Independent Flind mobile native identity migration

**State: NO-GO, staged engineering.** The candidate bundle/package identifier is `com.thehalfmoon.flind.mobile`. Its iOS and Android store identifiers are **not registered**. Their registration **has not been performed, the identifier is not verified to be available or owned, and no certificate, provisioning profile, Firebase service, app-link domain or signing key has been created**. Do not submit this app or build a public release.

## Identity contracts

| Build | Display name | Native iOS/Android ID | OAuth/deep-link scheme |
| --- | --- | --- | --- |
| Production | Flind | `com.thehalfmoon.flind.mobile` | `flind://` |
| Preview | Flind Preview | `com.thehalfmoon.flind.mobile.preview` | `flind-preview://` |
| Development | Flind Dev | `com.thehalfmoon.flind.mobile.dev` | `flind-dev://` |

The mobile app, backend Apple/Android app-link statements, development OAuth callback registration, React Native variant resolution, shared session-handoff protocol, native iOS App Groups and chart-widget Keychain services, Android Kotlin namespace/source paths, Expo module registries, Android notification-intent and widget manifests, and local smoke tests are migrated together. The app is a **new application**; it cannot impersonate or update the original app. No original app secure storage or tokens are migrated. New push tokens, installation IDs, App Groups, widgets and local data may differ.

The mobile JavaScript project and a number of source paths retain third-party SDK package names where the runtime dependency still requires them. Do not remove mandatory copyright/licensing/provenance. The native rebrand does not mean all SDKs, logos, signatures or environment variables are finished.

## Before merging and before any release

1. Run exact-head Node native identity guard, mobile TypeScript, Jest, Biome, Python backend app-link/OAuth tests, build and compile Android native modules with the new package paths, and simulator iOS/Android navigation. Inspect associated-domain JSON and Android asset links under the actual Flind backend, with test certificates.
2. Register and confirm both identifiers under the operator's actual Apple/Google developer accounts. If unavailable, select a different namespace before any signed binary and update **all** references and tests.
3. Provision distinct Flind-owned EAS account/project, signing certificates/Apple team and Android key, Firebase/APNs push credentials, hostnames, associated-domain entitlements and OAuth public clients. Verify private signing credentials are absent from Git.
4. Replace all inherited artwork and native/store-facing brand assets with approved Flind images. Verify privacy/support/AI-processing disclosures and accepted legal policy URLs.
5. Confirm no inherited PostHog-hosted data flow or production OTA update target; OTA is disabled by default. Run realistic signed install/update/uninstall tests, crash/recovery, deep-link OAuth flow and consent, privacy and tenant isolation E2E.
6. Publication, store submission and package release remain prohibited without the owner's explicit **GREEN LIGHT FLIND**.

This file documents **staged code** only, not completion or verified readiness.
