# Flind desktop telemetry: default-off, owned-host contract

**Independent Flind desktop builds must never inherit the source vendor's metrics, replay, crash or log collection infrastructure.**

All three desktop telemetry entry points now require explicit Flind operator build configuration:

- `VITE_FLIND_ANALYTICS_KEY`: project key of the Flind operator's collection service
- `VITE_FLIND_ANALYTICS_HOST`: HTTPS collector origin (no userinfo, path, query or fragment)
- `VITE_FLIND_ANALYTICS_UI_HOST`: optional separately operated HTTPS UI origin; defaults to the validated Flind collector origin

When the key or valid HTTPS collector is absent, the renderer analytics client does not initialize, Electron's posthog-node client does not initialize, and OTLP log export is a no-op. No analytics or log endpoint defaults to the previous upstream operator, and old `VITE_POSTHOG_API_KEY` or `VITE_POSTHOG_API_HOST` are not used by these clients. A configured `VITE_FLIND_ANALYTICS_UI_HOST` that fails validation disables the renderer client, not silently falling back.

The common validator rejects the previous operator's .posthog.com and .posthog.dev hostnames, HTTP, userinfo and URL paths. It cannot independently verify ownership of arbitrary third-party hostnames: the operator must configure only domains they control. Disabling analytics is not a substitute for network egress tracing of every other product integration.

**Release NO-GO:** The PostHog JavaScript/Node SDK dependencies are still third-party packages; any enabled renderer analytics may still use remote feature flags/session recording. A real privacy and consent review is needed before enabling them. Validate all renderer/main-process network egress and exception/log content on signed Windows and macOS builds, and independently audit all build-time sourcemap upload plugins and auxiliary desktop/cloud services. No vendor credentials, public release or paid infrastructure are provisioned by this patch.
