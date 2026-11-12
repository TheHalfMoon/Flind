# Flind mobile analytics: explicit opt-in

By default, Flind mobile starts **without a telemetry SDK client**, no upstream cloud analytics endpoint, and no transmitted analytics events. The previous built-in upstream collector default is removed.

To enable telemetry in a Flind-controlled build, explicitly configure all of:

- `EXPO_PUBLIC_FLIND_ANALYTICS_KEY`: project key issued by the Flind deployment
- `EXPO_PUBLIC_FLIND_ANALYTICS_HOST`: HTTPS origin of the Flind-controlled collection endpoint

The collector validator rejects the inherited third-party cloud domains, userinfo in URLs, HTTP, paths and query fragments. A missing or invalid host prevents initializing the SDK even when a key is present. The SDK remains an upstream library dependency; renaming/vendoring it is a **separate** stage and needs transport and on-device verification.

Optional development-only features use `EXPO_PUBLIC_FLIND_ANALYTICS_REPLAY=1` and `EXPO_PUBLIC_FLIND_ANALYTICS_HANDOFF=1`. Replay remains restricted to an opted-in internal build in demo mode after hydration while signed out; mask-all and no-network-capture settings remain active.

There is no Flind-operated telemetry endpoint bundled or provisioned by this patch. Production release is blocked until native behavior, ingress and privacy disclosures have been independently qualified.
