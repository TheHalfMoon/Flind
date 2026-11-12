# Flind browser OAuth token redirect isolation

Flind Web OAuth is an independently configured HTTPS OAuth client. It uses the selected Flind Cloud operator's OAuth endpoints and a browser callback at `/callback`. Authorization codes and refresh tokens are **credentials** and must never follow HTTP redirects that might forward their POST bodies to another origin.

Both flows share `postTokenEndpoint`, which now sets Fetch `redirect: "error"`, explicitly rejects any 3xx response surfaced by the adapter, and does not retry to a redirected destination. A legacy browser callback channel name is replaced with a Flind-only name.

Synthetic tests exercise HTTP 301, 302, 303, 307 and 308 plus a Fetch redirect failure; they assert a single request to the explicitly configured Flind origin with the no-redirect policy. They do not issue any live requests.

**Release NO-GO:** Verify Flind-operated OAuth service, public client registration, CORS policy, callback URI and state/PKCE binding, on-browser code and refresh exchanges, and real cross-origin 307/308 traffic capture with an instrumented test service. The hosted OAuth server and user account service are not provisioned by this patch. No external identity provider or public deployment has been enabled.
