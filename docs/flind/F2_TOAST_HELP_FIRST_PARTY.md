# Flind F2 — error-toast help fallback

Previously the error toast's **Get help** fallback and the standalone support
function opened a vendor-owned help page. That bypassed the first-party
navigation rules already applied to the main menus.

Now `openSupportOptions` consults the same validated operator-provided
`flindPublicUrl('docs')` as the other Flind UI surfaces. When no real
first-party docs destination has been configured, the function makes **no
outbound request**. It does not invent a URL or borrow an upstream website.

When docs are configured, the original approved URL's query is preserved
and `utm_medium` / `utm_campaign` are encoded via `URLSearchParams`.
The new tab is opened with `noopener,noreferrer`.

The `setGetHelpAction` registration seam is unchanged: if the application
has installed its own in-app support action, it continues to take priority
over the standalone docs fallback.

## Qualification

- `tools/flind/test_toast_help_boundary.py` guards against a regression
  to a hard-coded third-party support URL.
- `frontend/src/lib/lemon-ui/LemonToast/getHelp.test.ts` includes Jest
  coverage for unconfigured docs, configured docs, safely encoded
  campaign tags, and the registered support action.
- **Full Jest and browser E2E were not run in this change**, because the
  connected desktop execution quota is exhausted. This is not a launch pass.

Prior to release, configure a verified Flind documentation destination,
run these tests with the complete frontend runtime, verify error-toast
click journeys in a browser, and pass the independent source-wide
identity and egress release gates. No publication.
