# Wave 145 — Flind-owned staff feedback and Slack destination

> **Historical document.** Upstream PostHog removed the staff-only internal feedback feature, and Flind
> took that removal in the upstream merge of `4efa693e9aec`. `posthog/api/internal_feedback.py` no longer exists, and
> `posthog/settings/integrations.py` no longer defines `INTERNAL_FEEDBACK_SLACK_CHANNEL`,
> `FLIND_INTERNAL_STAFF_EMAIL_SUFFIX`, or the other internal feedback settings. The changes below describe code that
> is no longer in the tree and are kept only as a record of Wave 145.

## Production safety and first-party identity defect

The optional staff-only UI feedback flow inherited **two non-Flind trust assumptions**:

- `INTERNAL_FEEDBACK_SLACK_CHANNEL` defaulted to a concrete upstream Slack channel ID, even though its bot token defaulted empty. If a Flind operator set only a bot token, feedback text and screenshots could be sent to an unrelated channel.
- `IsPostHogStaffEmail` authorized verified users based on the upstream company's email suffix, not a domain controlled by the operator of Flind. This both fails to recognize legitimate Flind staff and potentially trusts the wrong organization's verified addresses.

## Actual production changes

- `posthog/settings/integrations.py`: `INTERNAL_FEEDBACK_SLACK_CHANNEL` defaults to **empty**, not a vendor-owned channel. New `FLIND_INTERNAL_STAFF_EMAIL_SUFFIX` defaults **empty** and must be set to an owned verified team email suffix, e.g. `@your-owned-domain.example`. No production Flind email domain is invented.
- `posthog/api/internal_feedback.py`: `is_flind_staff_email` and `IsFlindStaffEmail` now check the **explicit** configured first-party email domain and `is_email_verified is True`. Missing/malformed settings are rejected; email case normalized. The existing authenticated-user and scope permissions remain unchanged.
- Existing API source refuses with **HTTP 503** when either Slack bot token or channel is missing **before creating a Slack client**. Without owned team email config, requests fail authorization before reaching any Slack delivery path.
- The public OpenAPI feedback description and permission message now say Flind.
- Strengthened the original Django API tests to use a synthetic `@flind.example` (test-only) email suffix and URL, and added regressions for missing channel (503; no Slack calls) and unconfigured team suffix (403; no Slack calls).

## Executed verification

On the connected Mac, fetched the exact GitHub branch into an isolated proof folder, and executed `tools/flind/test_internal_feedback_flind_admission_wave145.py` under pinned CPython 3.14.7.

**5/5 PASS, exit 0:**
1. Real `FLIND_INTERNAL_STAFF_EMAIL_SUFFIX` settings expression defaults to empty; verified example staff is denied when unconfigured.
2. Both Slack channel and token default empty.
3. Actual source `is_flind_staff_email()` accepts only a configured domain with verified matching email, with case normalization.
4. Empty/malformed/non-string suffix refuses rather than allowing internal access.
5. Explicit destination settings are honored, original API still requires both token and channel, and Django regressions for no egress/no domain are present.

This test compiles the **actual source function AST**; it does **not** invoke Slack, the Django app, any database or external network. Full original Django API test suite is updated but **not run**, because the source checkout for the 451-package locked runtime remains sparse and does not yet qualify Django app registry.

## Remaining gates

The staff email suffix, actual Slack workspace/channel, credentials and Flind-owned customer support/community flow still need operator provisioning before this optional integration can be activated. Do not hardcode a real destination. Full Django runtime, auth, worker ingest, tenant isolation, and browser E2E remain release blockers (#82); identity migration remains in #5. No release/deploy/paid services, private repo, inherited Actions disabled and legally required attribution preserved.
