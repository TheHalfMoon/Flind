# Flind — first-party onboarding legal and support links

The inherited organization creation screen linked to **another vendor's
Terms of Service and Privacy Policy** while telling users they were agreeing
to those policies. The preflight setup screen likewise routed users to
unrelated support, deployment and troubleshooting pages.

## Implementation

- Extend `flindPublicUrl()` to allow only explicitly configured
  `terms` and `privacy` pages, alongside the existing docs/community.
- The environment variables are `VITE_FLIND_TERMS_URL` and
  `VITE_FLIND_PRIVACY_URL`. URLs must pass the existing exact HTTPS
  hostname check bound to `VITE_FLIND_WEBSITE_HOST`.
- **Both** legal URLs must exist and pass validation before the application
  displays an account-creation consent statement. Without both, it does
  not falsely claim another company's policies apply; instead, it tells
  users that their Flind administrator must provide legal information.
- Replace inherited support and troubleshooting links in preflight setup
  and organization creation with operator-configured Flind docs/community.
  If these are missing, show local administrator guidance, not a broken
  outbound link.
- Remove inherited vendor naming and example organization placeholder
  from organization creation.

## Qualification and release requirements

- Extend first-party URL unit tests and add dependency-free source checks
  for onboarding routes, legal policy gating and default help behavior.
- UI integration, Jest and browser E2E remain **NOT RUN** because the
  connected desktop execution quota is exhausted and Actions are disabled.
- A verified Flind-owned legal policy and proper account-consent review
  are required before a public sign-up launch. Configuring URLs alone is
  not a substitute for legal review.
- This is not a complete identity, distribution or release qualification.
  Repository must remain private; **NO-GO**.
