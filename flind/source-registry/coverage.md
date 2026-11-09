# Flind source registry: coverage

Generated from the GitHub API listing of every repository in the `PostHog` organisation that is visible
to the authenticated account (`gh api --paginate orgs/PostHog/repos?type=all`). No private repositories were
visible, so category 12 is empty; private repositories, if any exist, are not covered and would need separate
authorization.

Files: `registry.json` and `registry.csv` (one row per repository), `classify.py` (the rules), `repos.tsv`
(the raw API listing).

## Totals

- Repositories discovered: **415**; classified: **415** (100%), unclassified: **0**.
- In scope for Flind (categories 1-5): **60**; needs a scope decision (6, 7, 8): **55**; out of scope (9, 10, 11): **300**.
- In-scope repositories are pinned to their default-branch head SHA on the listing date.

| Category | Repositories |
| --- | ---: |
| Unrelated or irrelevant | 170 |
| Archived or superseded source | 108 |
| CLI, MCP, wizard, or developer tooling | 34 |
| Integration or plugin | 23 |
| Example or template | 22 |
| Active SDK | 17 |
| Shared infrastructure | 17 |
| Deployment and operations | 15 |
| Website and documentation | 4 |
| SDK specification or test harness | 3 |
| Core application | 2 |

## In-scope repositories

| Cat | Repository | License (SPDX) | Pinned SHA | Revision date | In Flind |
| ---: | --- | --- | --- | --- | --- |
| 1 | [posthog](https://github.com/PostHog/posthog) | NOASSERTION | `bb6faaec35d2` | 2026-11-09 | yes (imported at cd26680c) |
| 1 | [posthog-foss](https://github.com/PostHog/posthog-foss) | MIT | `449f81566398` | 2026-11-09 | no |
| 2 | [posthog-android](https://github.com/PostHog/posthog-android) | NOASSERTION | `677547a0c40b` | 2026-11-09 | no |
| 2 | [posthog-dotnet](https://github.com/PostHog/posthog-dotnet) | MIT | `ad593e0d5654` | 2026-11-09 | no |
| 2 | [posthog-elixir](https://github.com/PostHog/posthog-elixir) | NOASSERTION | `cfb156af9572` | 2026-11-09 | no |
| 2 | [posthog-flutter](https://github.com/PostHog/posthog-flutter) | NOASSERTION | `eb79b761cc46` | 2026-11-09 | no |
| 2 | [posthog-go](https://github.com/PostHog/posthog-go) | MIT | `2f949f18e277` | 2026-11-06 | no |
| 2 | [posthog-godot](https://github.com/PostHog/posthog-godot) | NOASSERTION | `21ec1c3d6064` | 2026-11-09 | no |
| 2 | [posthog-ios](https://github.com/PostHog/posthog-ios) | NOASSERTION | `2df563fe65f8` | 2026-11-09 | no |
| 2 | [posthog-js](https://github.com/PostHog/posthog-js) | NOASSERTION | `f2bd65d98173` | 2026-11-09 | no |
| 2 | [posthog-kmp](https://github.com/PostHog/posthog-kmp) | MIT | `8e8e881a32d5` | 2026-11-09 | no |
| 2 | [posthog-laravel](https://github.com/PostHog/posthog-laravel) | MIT | `ee72e7d1fd1d` | 2026-11-09 | no |
| 2 | [posthog-php](https://github.com/PostHog/posthog-php) | MIT | `0edda86494c8` | 2026-11-09 | no |
| 2 | [posthog-python](https://github.com/PostHog/posthog-python) | NOASSERTION | `c78e7bb7c543` | 2026-11-09 | no |
| 2 | [posthog-roblox](https://github.com/PostHog/posthog-roblox) | MIT | `cef6b1e8db93` | 2026-11-06 | no |
| 2 | [posthog-rs](https://github.com/PostHog/posthog-rs) | MIT | `ea5a562fb41d` | 2026-11-09 | no |
| 2 | [posthog-ruby](https://github.com/PostHog/posthog-ruby) | NOASSERTION | `97102efc5ca6` | 2026-11-09 | no |
| 2 | [posthog-unity](https://github.com/PostHog/posthog-unity) | NOASSERTION | `c440a45b3a9a` | 2026-11-09 | no |
| 2 | [posthog-unreal](https://github.com/PostHog/posthog-unreal) | MIT | `97d187e20e63` | 2026-10-23 | no |
| 3 | [error-tracking-harness](https://github.com/PostHog/error-tracking-harness) | NONE | `13924cf49993` | 2026-10-28 | no |
| 3 | [posthog-sdk-test-harness](https://github.com/PostHog/posthog-sdk-test-harness) | MIT | `097d69ea9c0b` | 2026-11-09 | no |
| 3 | [sdk-specs](https://github.com/PostHog/sdk-specs) | NONE | `8306698577b4` | 2026-11-09 | no |
| 4 | [ai-plugin](https://github.com/PostHog/ai-plugin) | NONE | `b1c977b5aae7` | 2026-11-09 | no |
| 4 | [check-package-version](https://github.com/PostHog/check-package-version) | MIT | `abc438f5bf48` | 2026-11-04 | no |
| 4 | [claude-code-share-plugin](https://github.com/PostHog/claude-code-share-plugin) | MIT | `9a86363fae86` | 2026-07-21 | no |
| 4 | [codex-share-plugin](https://github.com/PostHog/codex-share-plugin) | MIT | `41dbe89b9bb6` | 2026-07-21 | no |
| 4 | [community-skills](https://github.com/PostHog/community-skills) | MIT | `df4ae7975e55` | 2026-09-28 | no |
| 4 | [context-mill](https://github.com/PostHog/context-mill) | NONE | `a169e6139de9` | 2026-11-07 | no |
| 4 | [depot-mcp](https://github.com/PostHog/depot-mcp) | MIT | `d3e9f7bb1691` | 2026-10-22 | no |
| 4 | [duckhog](https://github.com/PostHog/duckhog) | MIT | `11ae95370786` | 2026-06-26 | no |
| 4 | [embedded-analytics-ui](https://github.com/PostHog/embedded-analytics-ui) | NONE | `b66a5a4ab1b0` | 2025-08-04 | no |
| 4 | [hogql-jdbc-driver](https://github.com/PostHog/hogql-jdbc-driver) | NONE | `07cb8be17ca5` | 2023-03-28 | no |
| 4 | [hogtyped](https://github.com/PostHog/hogtyped) | NONE | `9411e8f1001b` | 2026-05-28 | no |
| 4 | [homebrew-tap](https://github.com/PostHog/homebrew-tap) | MIT | `f548f940f443` | 2026-11-09 | no |
| 4 | [libdebugger](https://github.com/PostHog/libdebugger) | NONE | `0c7b5c07d04b` | 2026-10-15 | no |
| 4 | [pi-posthog](https://github.com/PostHog/pi-posthog) | MIT | `b91ff1889ecb` | 2026-07-09 | no |
| 4 | [posthog-annotate-merges-github-action](https://github.com/PostHog/posthog-annotate-merges-github-action) | NONE | `582004fed186` | 2024-09-05 | no |
| 4 | [posthog-definitions](https://github.com/PostHog/posthog-definitions) | NONE | `3af9dd20bbb9` | 2026-07-27 | no |
| 4 | [posthog-extension-legacy](https://github.com/PostHog/posthog-extension-legacy) | MIT | `b90c09d5ef41` | 2026-05-28 | no |
| 4 | [posthog-for-github](https://github.com/PostHog/posthog-for-github) | NONE | `7b5672aa9eac` | 2026-10-15 | no |
| 4 | [posthog-github-action](https://github.com/PostHog/posthog-github-action) | NONE | `426cbb535f6b` | 2026-06-24 | no |
| 4 | [posthog-migrate-meta](https://github.com/PostHog/posthog-migrate-meta) | NONE | `8d3cd3428bf4` | 2026-07-24 | no |
| 4 | [posthog-migration-tools](https://github.com/PostHog/posthog-migration-tools) | NONE | `c29d07ba14e4` | 2026-05-21 | no |
| 4 | [posthog-openclaw](https://github.com/PostHog/posthog-openclaw) | MIT | `70e740e0a9dc` | 2026-11-09 | no |
| 4 | [posthog-opencode](https://github.com/PostHog/posthog-opencode) | MIT | `8e218951cf76` | 2026-11-09 | no |
| 4 | [posthog-pi](https://github.com/PostHog/posthog-pi) | MIT | `2f2739646a7e` | 2026-11-09 | no |
| 4 | [posthog-vscode](https://github.com/PostHog/posthog-vscode) | MIT | `8b9a8367f8a5` | 2026-08-05 | no |
| 4 | [posthog-watcher-action](https://github.com/PostHog/posthog-watcher-action) | MIT | `41f5037922fe` | 2026-10-22 | no |
| 4 | [product-tours-debugger](https://github.com/PostHog/product-tours-debugger) | NONE | `b1d3c20a5041` | 2026-08-05 | no |
| 4 | [resolve-release](https://github.com/PostHog/resolve-release) | NONE | `52d3bea6f86a` | 2026-09-23 | no |
| 4 | [skills](https://github.com/PostHog/skills) | MIT | `3dbb006b9c84` | 2026-11-09 | no |
| 4 | [terraform-provider-posthog](https://github.com/PostHog/terraform-provider-posthog) | MPL-2.0 | `dad670bead02` | 2026-11-09 | no |
| 4 | [upload-source-maps](https://github.com/PostHog/upload-source-maps) | NONE | `bbfc8eae6d9e` | 2026-06-08 | no |
| 4 | [warlock](https://github.com/PostHog/warlock) | MIT | `5a0939d588b7` | 2026-10-15 | no |
| 4 | [wizard](https://github.com/PostHog/wizard) | MIT | `df7de25c4642` | 2026-11-07 | no |
| 4 | [wizard-workbench](https://github.com/PostHog/wizard-workbench) | MIT | `6c3c48af04b3` | 2026-11-06 | no |
| 5 | [docs-freshness](https://github.com/PostHog/docs-freshness) | NONE | `063d4f29a71b` | 2026-10-22 | no |
| 5 | [learn](https://github.com/PostHog/learn) | MIT | `ac6b307c3027` | 2026-03-24 | no |
| 5 | [posthog-docusaurus](https://github.com/PostHog/posthog-docusaurus) | MIT | `2842544bda0a` | 2026-05-21 | no |
| 5 | [posthog.com](https://github.com/PostHog/posthog.com) | NOASSERTION | `d47743ee94f1` | 2026-11-09 | no |

## Notes

- **Core:** `posthog` was imported into Flind at `cd26680c84533f65f43e1c7efc701bf792a5363a`. Its current upstream
  head is listed above; the difference is the Stage 3 upstream delta. `posthog-foss` is the MIT-only mirror and
  serves as the licensing boundary reference for `ee/`.
- **SDKs not listed separately:** the Node SDK, React Native and `posthog-js-lite` are maintained inside the
  `posthog-js` monorepo, so that entry covers them.
- **Licensing:** 29 in-scope repositories declare no SPDX license (`NONE`) or `NOASSERTION`.
  The owner attests full permission to copy and rename PostHog source (see `docs/flind/SOURCE_PROVENANCE.md`);
  each import must still keep the upstream copyright and license files.
- **Hosted dependencies:** repositories whose purpose is a PostHog-operated service (for example the billed LLM
  gateway integration) are classified but out of scope for a self-hosted Flind.
- **Categories 6-8** (deployment, integrations, shared infrastructure) are marked `review`: they are imported only
  when a product capability needs them.
- Integration status, test results and target Flind directories are filled in per repository as each is imported.
