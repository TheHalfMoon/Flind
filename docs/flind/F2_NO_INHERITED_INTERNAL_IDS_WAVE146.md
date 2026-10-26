# Wave 146 — Remove inherited internal Flind project and analytics team IDs

## Production defect

The source-defined defaults for two security-sensitive first-party scopes still assumed IDs belonging to an unrelated upstream cloud:

- `POSTHOG_PROJECT_ID = 2` in `posthog/settings/base_variables.py`, consumed by transactional-email delivery. A fresh Flind installation must **not** assume project ID 2 belongs to its owner; if only an email API key were added, the old default could target an unrelated or unintended project.
- `LLM_ANALYTICS_INTERNAL_TEAM_ID = 2`, consumed by the internal personal LLM-spend API and trace metadata. A fresh Flind instance must not silently query or tag a fixed team ID.

## Implementation

- A new first-party `FLIND_PROJECT_ID` environment setting takes priority. Existing `POSTHOG_PROJECT_ID` configuration remains a compatibility fallback for downstream integrations until their contracts are migrated. Both are now **unset/zero by default**, not the upstream project ID.
- The internal team reads `FLIND_LLM_ANALYTICS_INTERNAL_TEAM_ID` with default **0**. No unverified owner ID or first-party cloud hostname is fabricated.
- The unchanged `posthog/transactional_email.py` admission already rejects `POSTHOG_PROJECT_ID <= 0`; this wave proves and preserves that fail-closed behavior. A correctly and explicitly configured Flind project and API key continue to pass this admission predicate.

`0` means not configured. This wave does **not** migrate stored database team identifiers, third-party SDK environment variables, external OAuth/Kafka/Redis endpoints, or make personal-spend queries valid with no configured Flind analytics team. Those require functional migration.

## Executed evidence (2026-10-26)

The exact GitHub branch's tracked files were fetched into a temporary isolated source fixture on the Mac. `tools/flind/test_first_party_internal_ids_wave146.py` evaluates the **actual Python settings assignment AST**, the **actual transactional-email admission function**, and the **actual internal team ID consumer** under pinned Python 3.14.7, without importing Django application registries or contacting any network, database, email API or LLM provider.

**6/6 PASS, process exit 0** covering:
1. New default project 0 refuses sending transactional email even with synthetic API token.
2. New default internal team 0.
3. Explicit `FLIND_PROJECT_ID` takes precedence over a legacy value; valid explicit project + key enables the existing admission predicate, missing key denies.
4. Explicit legacy env variable remains functional until consumers migrate.
5. Explicit owner-controlled analytics team configuration is honored.
6. Zero and negative projects reject outbound email, even if an API token is configured.

## Qualification limits

This is a focused first-party security/identity default fix with **real logic execution**. It is **not** a full authenticated Django API/transactional email integration test, nor LLM-spend correctness, nor qualified OAuth/PKCE, SDK→Kafka→ClickHouse→Dashboard E2E. Source identity issue #5 and end-to-end release gate #82 remain OPEN; release NO-GO. Repository private, inherited Actions disabled, no publication/deployment or paid services, legal attribution preserved.
