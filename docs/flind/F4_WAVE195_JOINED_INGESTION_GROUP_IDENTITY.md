# Flind Wave 195 — collision-free joined ingestion grouping identity

## Original production defect and repair (27 October 2026)

The original `nodejs/src/ingestion/pipelines/analytics/joined-ingestion-pipeline.ts`
grouped event-processing work with `getTokenAndDistinctId()`:

```ts
return `${token}:${distinctId}`
```

This is not an injective representation of the (token, distinct_id) pair.
For example, `("alpha:beta", "gamma")` and
`("alpha", "beta:gamma")` both map to `alpha:beta:gamma`.
There is a similar collision for `("", ":")` and `(":", "")`.
The key is passed into production `concurrentlyPerGroup`. A collision
could make distinct identities share a processing group, changing
scheduling and ordering. This test does **not** prove a production
data leak or a cross-tenant authorization bypass.

The original method now uses an unambiguous length-prefixed token:

```ts
return `${token.length}:${token}${distinctId}`
```

The token is always a string (falling back to `''`); the exact token
length before the first colon uniquely identifies the token boundary,
leaving the entire remaining suffix as distinct_id. Colon, Unicode,
newlines and empty strings no longer make different pairs indistinguishable.
No wire format, stored event property, external API or SDK identifier
was changed.

### Actual red/green evidence

```bash
node --test tools/flind/test_joined_ingestion_group_key_wave195.mjs
node --test tools/flind/test_production_grpc_driver_wave192.mjs
```

Before the product patch, executing the **actual source-extracted Flind
grouping function** yielded **3/7 pass and 4/7 fail**: concrete colon
collisions, empty-key ambiguity, Unicode ambiguity and an exhaustive
bounded test failed. The test runner reads the production TypeScript
source, strips only TypeScript syntax using Node, runs that actual
function in a VM, and checks the production factory still passes it to
`concurrentlyPerGroup`. It does not use a rewritten mock implementation.

After repair: **7/7 pass** including **1,600 distinct synthetic
(token, distinct_id) pairs**, and Wave192's production-driver
regressions **8/8 pass**; `git diff --check` passed. Tests used
Node 26 locally, no packages or network.

### Qualification limits

This fixes a specific original production grouping-key collision but
does **not** qualify the complete joined ingestion pipeline under load,
side effects, multi-worker Kafka rebalancing, production ClickHouse
dedup, authorization/tenant isolation, full Python/Django runtime, or
SDK-to-dashboard E2E. The broader release and branding gates remain
unqualified. Flind repository remains PRIVATE with Actions disabled.
No publish, deployment, paid model use or customer data.
