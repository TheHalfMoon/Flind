# Flind mobile: Expo publishing isolation

This repository does not automatically use the original application's Expo account, EAS project, Apple app ID, or cloud associated domains. All Expo OTA updates are disabled for all variants until Flind's own release signing is configured, independently reviewed and tested.

For local development, no hosted Expo account or EAS project is needed. For a future Flind-owned hosted build, configure both `FLIND_EXPO_OWNER` and `FLIND_EXPO_PROJECT_ID` with values from an account and project you control. They have no fallback. Configure optional `EXPO_PUBLIC_FLIND_US_HOST` and `EXPO_PUBLIC_FLIND_EU_HOST` only with real HTTPS origins you control.

The source's native bundle identifiers, native iOS target, signing, Android package, embedded entitlements, callback schemes, OAuth client IDs, icons and links still require end-to-end Flind-specific migration and store/device qualification. Do not submit, distribute or install this as a production Flind mobile app yet.

All builds and submissions remain manual and gated; this patch does not initiate a publish, hosted update or EAS operation.
