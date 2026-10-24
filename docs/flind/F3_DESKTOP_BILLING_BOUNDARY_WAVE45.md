# Wave 45 — Independent Flind billing or no payment action

## Confirmed inherited issue

The Desktop usage-limit modal and Plan & Usage settings still generated
an inherited provider billing page and legacy product SKU from the
selected cloud region. An admin could be directed to the original
vendor's payment flow, rather than any independently owned Flind billing
agreement. The model/usage content also claimed provider-specific credit
limits and unqualified pay-per-use terms.

## Fix

- Make getBillingUrl require an explicit first-party URL, checked
  against VITE_FLIND_CLOUD_APP_HOST using the existing strict HTTPS
  URL validator. The operator supplies VITE_FLIND_BILLING_URL.
- Region IDs no longer imply that the inherited provider owns a Flind
  payment destination; preserve the getBillingUrl signature to avoid
  breaking existing call sites.
- When no valid billing URL exists, suppress the action button on the
  usage-limit dialog; preserve dismiss and an honest unavailable notice.
- The existing Plan & Usage buttons already disable when billingUrl is
  null; they now receive null until independent billing is configured.
- Remove claims that the original vendor's credit limits or payment
  pricing apply to Flind. Preserve distinct model-unavailable and
  model-access states; do not invent a Flind price, payment processor or
  supported plan.

## Executed evidence

- URL/billing modal React/Vitest: 17/17 PASS.
- Core usage-limit content tests: 12/12 PASS.
- Source regression guards enforce the first-party URL requirement,
  protected upgrade button and absence of old credit/pricing copy.
- Full Flind Python suite: **326/326 PASS**.
- Full @flind/core TypeScript: **PASS**, zero errors.
- Full @flind/ui TypeScript: **PASS**, zero errors.
- Three source containment regression cases: PASS.
- Staged diff/whitespace checks: PASS.

## Remaining NO-GO

No Flind payment processor, plan definitions, terms, accounting, tax or
chargeback path was configured; a valid URL alone does not qualify
payments. No payment was attempted. Backend subscription limits,
usage ingestion, server auth/permissions and billing-service E2E remain
unverified. Repo private, inherited GitHub Actions disabled, no
deployment or public release.
