# Flind — rebranding strategy

## Change in layers, not blind global search-and-replace

**Layer A: end-user-visible branding**
- Browser title and metadata: `posthog/templates/head.html`
- PWA name: `frontend/public/site.webmanifest`
- Reauthorization title: `posthog/templates/sso_reauth_complete.html`
- README, public copy, onboarding, auth screens, emails, error screens, navigation, product help links
- Static assets (favicons, logos, mascot artwork, app icons, social previews)
- Default display names and external URLs routed to the original service

**Layer B: product configuration and deployment**
- Container images, registries, domains, Docker services, CSP/CORS allowed hosts
- Environment variables, imported connectors, billing/payment endpoints, OAuth redirect origins
- GitHub Actions and release scripts; all **disabled** until reviewed
- Frontend bundles, third-party script loaders, telemetry and bug reporting

**Layer C: protocols and legacy identifiers**
- Python modules named `posthog`, API event names, JS globals, package identities, database schemas/migrations and SDK wire formats
- Retain behind explicit compatibility adapters until paired migration tests exist.
- Never rename durable event properties, migrations or query identifiers as cosmetic changes.

**Layer D: legal, historical and third-party references**
- Retain license and required attribution material; references that identify provenance are not product-brand defects.
- Permission to rename product identity is not a technical reason to mutate source authenticity records.

## Gate F1 visual checklist

- [ ] Flind wordmark + icon across dark/light themes and small sizes
- [x] Primary HTML title and social/application metadata
- [x] Web app manifest name
- [x] Main README and developer starting point
- [ ] Navigation, auth, email, errors, onboarding and documentation
- [ ] Assets/favicons/mascot removed or replaced with original Flind design
- [ ] No upstream-hosted image/script/service required for first-run experience
- [ ] Full end-user screenshots and smoke tests on a clean local instance

## Technical audit suggestions

Use `rg -l -i 'posthog|hedgehog|hogql' frontend/ posthog/ products/ services/` to discover candidates; tag each match as branding, protocol, dependency, content, tests or provenance before changing it.

**Stop conditions:** a rename changes a public API, migration, network endpoint, stored identifier, client import path, published package name or external API contract without an accompanying compatibility test.
