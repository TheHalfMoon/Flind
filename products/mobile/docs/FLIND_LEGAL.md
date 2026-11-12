# Mobile legal destinations and AI disclosure

Flind mobile must not present policies, support contracts or consent documentation belonging to another organization as its own. The app previously linked to inherited third-party privacy, terms, support and AI policy pages. This change removes those URLs from the code.

Provide actual, published, HTTPS Flind-controlled destinations using the build-time variables `EXPO_PUBLIC_FLIND_PRIVACY_URL`, `EXPO_PUBLIC_FLIND_TERMS_URL` and `EXPO_PUBLIC_FLIND_SUPPORT_URL`. These are optional for development and must not refer to the inherited provider or its subdomains. The app does not invent substitute contracts or infer a document exists from a domain.

Until configured, the corresponding links are hidden, and consent to send user data to AI model providers cannot be given through the mobile AI consent sheet. Existing sign-in and non-AI self-hosted functions remain available. Deleting an account continues to open the signed-in Flind server's own settings page.

**Release remains blocked:** hiding missing links is not compliance. Before distribution, adopt and publish accurate Flind privacy, terms, support, AI provider/data-processing disclosures and verify their content against actual data flows, subscriptions, third-party processors, jurisdictional requirements, and the accessible web/mobile UI. Qualify the behavior on real iOS/Android devices with E2E tests. This PR does not itself authorize publishing.
