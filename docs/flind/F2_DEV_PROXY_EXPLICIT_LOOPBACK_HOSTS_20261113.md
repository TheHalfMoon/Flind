# Flind dev proxy: explicit loopback host compatibility

Status: source-contract and Docker Compose YAML validation passed locally;
**real Caddy HTTP routing test pending exact-head GitHub CI**.

## Background

Caddy's host matching treats `localhost` and `127.0.0.1` as
different hostnames. Flind's private Node SDK correctly disallows insecure
HTTP origins except numeric loopback, but the development proxy initially
advertised only `http://localhost:8000`, while the host port
`127.0.0.1:8010:8000` was bound to the local machine.

Official Caddy documentation explicitly confirms that a site configured
for `localhost` does not match requests addressed to `127.0.0.1`, and
supports comma-separated explicit site addresses:
https://caddyserver.com/docs/caddyfile/concepts

## Change

In **docker-compose.dev.yml only**, the proxy's default site addresses
now explicitly include `http://localhost:8000` **and**
`http://127.0.0.1:8000`. No catch-all or wildcard host was added.
The host-exposed proxy port remains **127.0.0.1:8010**, not a
publicly reachable interface.

An operator-provided `CADDY_HOST` still overrides this dev default;
an override must configure its intended owned hosts independently.
The production/base compose configuration remains unchanged.

## Qualification

`node --test frontend/bin/flind-dev-proxy-loopback.test.mjs` checks
the restricted port mapping, exact two-host default, existing capture
routing and CI integration. `docker compose -f docker-compose.dev.yml
config --quiet` validates Compose interpolation; warnings may occur
for unrelated unset optional variables.

The branch-scoped real-service GitHub workflow additionally starts the
actual Caddy dev proxy after the local Django server has become healthy,
then requires both `http://localhost:8010/_health` and
`http://127.0.0.1:8010/_health` to return successful HTTP responses.
Neither a source test nor YAML validation alone proves a Caddy route.

This is a development-only compatibility gate. It does **not** prove
public HTTPS service ownership, production DNS, SDK event delivery, tenant
isolation, secure cookies, certificate provisioning or production egress
restrictions. These remain separate release blockers.

No public release, deployment, tag or SDK publication without explicit
owner authorization `GREEN LIGHT FLIND`.
