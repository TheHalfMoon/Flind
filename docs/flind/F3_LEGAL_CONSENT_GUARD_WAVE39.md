# Wave 39 — Mobile consent fail-closed until Flind-specific legal review

## Underlying issue

The inherited first-run consent screen presented PostHog AI processing and
Desktop beta terms as if they were applicable to Flind. It explicitly named
old processing vendors, linked to the original vendor's subprocessors and
allowed the Flind user to approve the inherited backend consent flags.
The page's support button linked to an inherited Discord community.

Rewording the claims to say "Flind" would create misleading and unverified
legal promises. These flows must not submit acceptance for another
organization's terms or advertise a different provider's privacy notices.

## Changes

- Replace the inherited consent-panel acceptance form with a factual,
  non-interactive explanation that independent Flind disclosures and terms
  must be reviewed before allowing onboarding.
- Preserve both outstanding backend gating signals (AI and beta terms) and
  the ability to log out. Do not bypass legal requirements with a default
  accepted state or mutate the inherited approval endpoints.
- Remove the submit callbacks and analytics calls from this mobile screen,
  along with its vendor legal link.
- Replace the inherited support community link with an honest "not
  configured" notice, instead of inventing a new support destination.
- Preserve the backend API schema and historic stored flags for compatibility,
  not as independent Flind legal acceptance records.

## Expected consequence

Organizations needing a new approval stay blocked at the consent screen.
This is an intentional development-time NO-GO, not an onboarding feature
completion. Re-enable acceptance only after legal review supplies Flind
policies, data-subprocessor declarations, consent UI and backend storage
semantics that match the deployed services, with security and E2E testing.

## Evidence and remaining limits

- Native Mobile original Vitest cases cover both outstanding statuses,
  administrator/non-administrator cases, no acceptance buttons and
  no external links. Source guards catch reintroduction of write calls
  and the inherited support URL.
- Full native Mobile Vitest: **740/740 PASS**; Studio Vitest **224/224 PASS**,
  combined **964/964 PASS**.
- Mobile and Studio TypeScript: PASS, zero Mobile baseline errors.
- Full Flind Python source regression suite **302/302 PASS**.
- This is no substitute for legal review. Native-device first-run paths,
  provider subprocessor behavior, backend deployment and full data-flow
  audit remain unverified.
- No release, public deployment, paid services or enabled inherited Actions.
  Repository remains private and mandatory source attributions preserved.
