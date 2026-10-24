# Wave 38 — Legacy forum SSO outbound data containment

## Confirmed risk in inherited code

The authenticated /api/user/redirect_to_website legacy route registered
users with squeak.posthog.cc, submitting their email, first/last name and
a newly generated password, before redirecting a signed session token to
posthog.com/auth. This destination and fallback signing key were not
configured for the independent Flind instance.

The toolbar authorization flow had a separate forum_login=true branch,
which accepted an inherited forum domain and rendered an account-linking
template with a link back into this legacy SSO route.

## Fail-closed changes

- Keep the old route for existing links but return HTTP 404 before reading
  user data, performing network I/O, signing tokens, or redirecting.
- Refuse the forum_login toolbar authorization branch before accessing
  user data; preserve the ordinary toolbar authorization flow and its
  project URL allowlist.
- Turn the unused legacy forum linking template into an honest unavailable
  message with no user email interpolation or active linking URL.
- Do not invent Flind forum hostnames, JWT secrets, or consent wording.

## Test evidence and limits

- Full Flind Python suite: **299/299 PASS** on macbook.
- Five behavioral tests compile/exercise the actual view functions with
  trapped external network and redirects and assert safe 404 behavior,
  including legacy domain, attacker domain and local host variants.
- Ordinary toolbar authorization is verified to render the original
  toolbar flow, not the forum-linking template.
- This lightweight harness avoids Django/database imports and is NOT
  evidence of a fully configured Django runtime, authorization middleware,
  or end-to-end browser SSO. Those release gates remain open.

## Operational policy

No deployment or publication. Preserve the private GitHub repository,
disabled inherited Actions, and legally required third-party attributions.
Re-enable forum SSO only if a first-party service, verified redirect
allowlist, session signing keys and explicit data-transfer consent exist.
