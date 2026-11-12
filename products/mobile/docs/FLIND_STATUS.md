# Flind mobile service status isolation

The previous mobile menu linked to the original operator's status service and polled its incident API when a cloud region was selected. **This is not a status page for Flind** and must not be used as such.

With this change, Flind mobile has **no status page by default**, makes no status polling requests and hides the Status action. A Flind operator may explicitly configure `EXPO_PUBLIC_FLIND_STATUS_URL` to the HTTPS origin of an actual Flind-controlled incident status service. URL validation rejects the original provider's status and cloud domains, non-HTTPS, embedded credentials, paths, queries and fragments.

When and only when a Flind cloud region and a valid status origin are configured and the session is live, the app fetches the incident API with `credentials: 'omit'`, `redirect: 'error'`, and scoped five-minute caching. Status and AI incident links point to the configured operator service. This patch does not create a status backend, require external paid status hosting, or make a claim that a service is operational.

Release NO-GO: verify a deployed status schema and Flind operator domain, harden network redirects at the native adapter, check 404/unavailable behavior, and test actual iOS/Android navigation before enabling it. No public deployment is authorized.
