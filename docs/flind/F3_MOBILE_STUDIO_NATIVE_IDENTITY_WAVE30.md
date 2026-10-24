# F3 Wave 30 — independent Mobile Studio native and update identity

## Observed risks

The second Expo application retained its imported vendor app name, dual URL
schemes, EAS publishing owner, remote EAS project identifier, iOS/Android
bundle IDs and live OTA update URL pointing to the original vendor's Expo
channel. The Apple App Transport Security configuration also allowed
arbitrary insecure HTTP transport. Notifications accepted arbitrary URL
protocols and mapped them to native navigation without app-scheme checks.

## Implementation

- Set app identity to Flind Studio, native scheme flind-studio, and
  provisional iOS/Android IDs com.thehalfmoon.flind.studio. These native
  identifiers are NOT store-qualified and no EAS project was created.
- Remove inherited Expo publishing owner and project identifier.
- Explicitly disable remote OTA updates and remove the inherited Expo
  updates URL. Keep the installed Expo updates module because the settings
  UI checks Updates.isEnabled and can hide its update controls.
- Remove arbitrary insecure HTTP permission from iOS App Transport
  Security while retaining local networking for controlled development.
- Change the app's OAuth redirect scheme to flind-studio; keep upstream
  wire-protocol field names pending backend contract migration.
- Use Flind/mobile-studio User-Agent identity.
- Accept push notification links only for Flind Studio task/report routes,
  never arbitrary URL schemes, external domains or unsafe path segments.
  Retain the historical taskId fallback when the identifier is valid.
- The imported local dev email, persistent storage key names and original
  backend OAuth redirect allowlists remain separate compatibility blockers.

## Verification

- Runtime checks executed the actual transpiled TypeScript notification
  path implementation under Node 24: 21/21 PASS.
- Python static regressions cover Expo app identity, disabled OTA, HTTPS
  transport requirement, callback scheme and notification path isolation.
- Full Flind Python regression 270/270 PASS; six TS/TSX files parsed with
  zero errors; git diff --check PASS on macbook, 2026-10-24.
- Mobile Studio's full Vitest/Expo/iOS/Android builds remain unavailable in
  the current lightweight checkout; no app-store registration, native app
  signing, backend OAuth callback E2E, push token or real OTA trace qualified.
- With the old EAS ID removed, push registration is intentionally unavailable
  until a separate first-party Expo project is provisioned. Do not publish.

Repository private. Inherited GitHub Actions disabled. Preserve required
third-party legal attributions. Flind release remains NO-GO.
