# Flind — Domain Connect identity isolation (F2 Wave 4)

## Decision

**Default: automatic DNS configuration OFF.** Flind has no independently
registered Domain Connect provider templates yet. Inherited provider IDs,
signing domains, and cloud callback URLs must never be used.

Manual DNS setup remains available. This change intentionally does **not**
claim DNS provider partnerships or a functioning automated DNS flow.

## Implementation

- `FLIND_DOMAIN_CONNECT_ENABLED` defaults to false.
- `FLIND_DOMAIN_CONNECT_PROVIDER_ID` defaults to the empty string. An
  operator must supply a valid, independently controlled provider domain and
  enable the feature after provider registration.
- `flind/domain_connect_identity.py` checks ID syntax and ensures callback
  URLs stay on `SITE_URL`, refusing credentials, fragments, off-site origins,
  port changes, insecure non-local HTTP and malformed URLs.
- The domain-check API returns `supported: false` without DNS discovery,
  tldextract initialization or provider calls when unconfigured.
- The apply API declines immediately before SES verification/proxy lookups or
  DNS operations if not configured, or if the callback is untrusted.
- The provider list is empty by default; backend apply URL construction uses
  `FLIND_DOMAIN_CONNECT_PROVIDER_ID`, not a hard-coded third-party identity.
- The four inherited provider template files were replaced by Flind draft
  templates with `.example` placeholders. They preserve the service IDs and
  parameter shapes needed for eventual template registration.

### Required prerequisites for live enablement

1. Choose and prove control of a Flind-owned DNS provider domain.
2. Publish approved Flind provider templates with verified logo, signing
   public-key domain and callback domains; all draft `.example` metadata
   must be replaced. The provider-ID validator rejects reserved and non-public
suffixes (including `.example`, `.test`, `.invalid`, `.local` and
`.internal`) so a draft cannot be activated accidentally.
3. Arrange actual registration/approval with intended DNS providers.
4. Configure the RSA signing key, key ID, Flind SITE_URL, and real provider ID.
5. Run integration tests with a disposable owned domain and validate every
   generated DNS record before enabling for end users.
6. Confirm proxy and email delivery flows with full end-to-end tests.

Only then set both `FLIND_DOMAIN_CONNECT_ENABLED=true` and
`FLIND_DOMAIN_CONNECT_PROVIDER_ID=<operator-owned-domain>`.

## Verification

- 57 Python standard-library static/pure tests PASS (8 added here).
- 8 foundation-brand checks PASS.
- All edited Python sources pass `py_compile`.
- The draft JSON templates parse and variable sets match backend resolver
  contracts (verification/DKIM/SPF/MX and proxy target).
- `git diff --check` PASS.

### Not verified

- Django integration tests (Django unavailable in current Python environment).
- Actual DNS providers, key publication, live DNS changes, browser/E2E.
- Full source-wide or packaged-binary zero-identity release gate.

The project is **not release qualified**, and source ownership/provenance
records must remain accurate. No hosting, DNS registration or deployment was
performed by this PR.
