# F1/F2 Wave 6 — website referrer trust

The login funnel previously classified visits from another product's public
website as trusted marketing referrals.

Flind now requires `VITE_FLIND_WEBSITE_HOST` to be explicitly set to a
first-party marketing hostname during frontend build. Unset = no trusted
marketing referrers. Accepted referrers must use HTTPS and exactly match the
configured host (no userinfo, no port, no phishing subdomains).

The marketing-domain unit tests use the reserved `flind.example` placeholder.
This is a **test-only domain**, not a deployment destination.

Verification: 49 standard-library tests passed, 8 brand entrypoint checks
passed, 3 touched TypeScript files passed syntax transpilation, and
`git diff --check` passed.

Full React/Vitest browser integration has not run. Any marketing referral UX
requiring a public Flind website is disabled until a real Flind-owned domain is
configured. Source-wide zero-identity and runtime qualification remain blocked.
