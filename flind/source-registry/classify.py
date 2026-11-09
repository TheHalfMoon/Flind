"""Classify every PostHog GitHub repository for the Flind source registry.

Input: repos.tsv from the GitHub API (name, archived, fork, private, visibility, license, default branch,
pushed_at, language, size_kb, description). Output: registry.json, registry.csv and coverage.md.
Classification is rule-based and deliberately conservative: anything not matched by a specific rule is
marked "unclassified-review" rather than guessed.
"""

import csv
import json
import re
import sys
from collections import Counter

CATEGORIES = {
    1: "Core application",
    2: "Active SDK",
    3: "SDK specification or test harness",
    4: "CLI, MCP, wizard, or developer tooling",
    5: "Website and documentation",
    6: "Deployment and operations",
    7: "Integration or plugin",
    8: "Shared infrastructure",
    9: "Archived or superseded source",
    10: "Example or template",
    11: "Unrelated or irrelevant",
    12: "Restricted or permission-dependent",
}

CORE = {"posthog", "posthog-foss"}
SDKS = {
    "posthog-js", "posthog-android", "posthog-ios", "posthog-flutter", "posthog-python", "posthog-ruby",
    "posthog-php", "posthog-go", "posthog-dotnet", "posthog-elixir", "posthog-rs", "posthog-kmp",
    "posthog-laravel", "posthog-unity", "posthog-unreal", "posthog-godot", "posthog-roblox",
    "posthog-react-native", "posthog-java",
}
SDK_QUALITY = {"sdk-specs", "posthog-sdk-test-harness", "error-tracking-harness"}
WEBSITE = {"posthog.com", "learn", "posthog-docusaurus", "docs-freshness"}
DEV_TOOLING = re.compile(
    r"^(ai-plugin|context-mill|skills|community-skills|posthog-vscode|posthog-extension-legacy|homebrew-tap|"
    r"terraform-provider-posthog|hogtyped|posthog-definitions|resolve-release|upload-source-maps|"
    r"posthog-github-action|posthog-annotate-merges-github-action|posthog-for-github|check-package-version|"
    r"posthog-migrate-meta|posthog-migration-tools|hogql-jdbc-driver|libdebugger|posthog-opencode|"
    r"posthog-openclaw|posthog-pi|pi-posthog|claude-code-share-plugin|codex-share-plugin|depot-mcp|"
    r"embedded-analytics-ui|product-tours-debugger|posthog-watcher-action|duckhog)$"
)
DEPLOY_OPS = re.compile(
    r"(helm|chart|terraform-aws|ch-podauth|container$|posthog-nginx-reverse-proxy|posthog-3000-installer|"
    r"emr-container|kafka-container|rust-node-container|metabase-clickhouse|empty-helm-chart|phlower|housekeeper|"
    r"partforge|HouseWatch|snuffle)"
)
INTEGRATION = re.compile(
    r"(-app$|plugin|posthog-segment|posthog-zapier|posthog-gtm-template|splunk-add-on|cookie-banner|"
    r"integrations-repository|discord-bot|bitbucket-release-tracker|sidecar)"
)
SHARED_INFRA = re.compile(
    r"^(chschema|clickhouse-json-drop-keys-udf|drf-exceptions-hog|django-nextgensquash|duckgres|hoglake|"
    r"millpond|duckstream|ducklake-metrics-daemon|ducklake-misc|kea-disposables|pixelhog|hothog|"
    r"property-taxonomy|terminal-assets|brand)$"
)
EXAMPLE = re.compile(r"(example|sample|demo|template|tutorial|playground|^support-|hoglabs|apps$|hedgebox)", re.I)
# Internal company tooling, games, bots and marketing: not part of the product.
UNRELATED = re.compile(
    r"^(\.github|DeskHog|HogTTV|PMF-game|birthday-bot|chesster|cool-numbers-club|dotfiles|guesshog|hedgehog-mode|"
    r"hedgehog\.vc|hedgehug|herdr|hogium|hogotchi|isgoogleanalyticsillegal\.com|jeeves|kudos|lmjtfy|mainframe|"
    r"marketing|meepslap|merch|open-sauce|ost-2025|owners-yaml-website|placeholder|posthog\.farm|postpile|"
    r"pr-assets|presentations|prs-are-just-colors-now|qr-mogging|requests-for-comments-public|sizeberg|stamphog|"
    r"survivors|synch|team-analytics-platform|team-devex|twig-components|camo-detector|coherence|hal-12000|"
    r"linux-posthogos|aili5|ai-research|gh-pr-assets|slack-canvas-updater|superday-docs|posthog-wii|"
    r"posthog-vscode-theme|benchmark-results|posthog-linter|internallinker|gatsby-source-squeak|hogtrace|"
    r"hoglite|artifacts|terraform-aws-sso-elevator|posthog\.com-og|posthog-csat|exported-recordings-analyzer|"
    r"session-data-comparanator|Session-Replay-Ingested-Blob-Desquashinator|app-dev-server)$"
)


# Reviewed by hand: repositories no rule matches, with the reason recorded.
OVERRIDES = {
    "docs": (9, "superseded: description says it was replaced by the posthog.com repository"),
    "wizard": (4, "setup wizard that adds the SDK to a project"),
    "wizard-workbench": (4, "test bench for wizard runs"),
    "warlock": (4, "agent security and hardening tooling"),
    "viaduck": (8, "Ducklake-to-Ducklake replication via CDC"),
    "pi-posthog-llm-gateway": (7, "integration that depends on PostHog's hosted, billed LLM gateway"),
    "analyze-surveys-with-chatgpt": (10, "tutorial code"),
    "posthog-hedgehog-adventure": (10, "demo game instrumented with the SDK"),
    "posthog-integration-planner": (10, "template to plan an integration"),
    "user-property-flag-test": (10, "feature flag test app"),
    "hackathon-ph-cli": (11, "hackathon prototype"),
    "visionhog": (11, "hackathon prototype"),
    "visual-review-extension": (11, "internal PostHog CI tool"),
    "workers-builds-notifications": (11, "internal notifications tooling"),
    "yc-badge": (11, "marketing badge"),
}


def classify(r):
    name = r["name"]
    if name in OVERRIDES and r["fork"] != "true" and r["archived"] != "true":
        return OVERRIDES[name]
    if r["private"] == "true":
        return 12, "private repository; requires separate authorization"
    if r["fork"] == "true":
        return 11, "fork of a third-party project; use the original upstream if ever needed"
    if r["archived"] == "true":
        return 9, "archived by PostHog"
    if name in CORE:
        return 1, "main application" if name == "posthog" else "MIT-only mirror; licensing boundary reference"
    if name in SDKS:
        return 2, "official SDK"
    if name in SDK_QUALITY:
        return 3, "cross-SDK contract or harness"
    if name in WEBSITE:
        return 5, "website or documentation"
    if DEV_TOOLING.search(name):
        return 4, "developer tooling"
    if SHARED_INFRA.search(name):
        return 8, "shared library or data infrastructure"
    if DEPLOY_OPS.search(name):
        return 6, "deployment or operations"
    if UNRELATED.search(name):
        return 11, "internal company tooling, game, bot or marketing; not part of the product"
    if INTEGRATION.search(name):
        return 7, "integration or plugin"
    if EXAMPLE.search(name):
        return 10, "example, demo or template"
    return 0, "unclassified-review"


def main(src):
    fields = ["name", "archived", "fork", "private", "visibility", "license", "default_branch", "pushed_at",
              "language", "size_kb", "description"]
    rows = [dict(zip(fields, line.rstrip("\n").split("\t"))) for line in open(src, encoding="utf-8") if line.strip()]
    out = []
    for r in rows:
        cat, why = classify(r)
        in_scope = cat in (1, 2, 3, 4, 5)
        out.append({
            "repository": f"https://github.com/PostHog/{r['name']}",
            "name": r["name"],
            "category_id": cat,
            "category": CATEGORIES.get(cat, "Unclassified - needs review"),
            "reason": why,
            "flind_scope": "in-scope" if in_scope else ("review" if cat in (0, 6, 7, 8, 12) else "out-of-scope"),
            "archived": r["archived"] == "true",
            "fork": r["fork"] == "true",
            "license_spdx": r["license"],
            "license_note": "owner-attested permission; no SPDX license declared upstream"
            if r["license"] in ("NONE", "NOASSERTION") else "SPDX license declared upstream",
            "default_branch": r["default_branch"],
            "last_push": r["pushed_at"],
            "language": r["language"],
            "size_kb": int(r["size_kb"] or 0),
            "description": r["description"],
            "commit_sha": None,
            "present_in_flind": "yes (imported at cd26680c)" if r["name"] == "posthog" else "no",
            "integration_status": "imported" if r["name"] == "posthog" else "not started",
        })
    out.sort(key=lambda x: (x["category_id"] or 99, x["name"].lower()))
    json.dump(out, open("registry.json", "w", encoding="utf-8"), indent=2)
    with open("registry.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    counts = Counter(x["category"] for x in out)
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{v:4}  {k}")
    print("unclassified:", [x["name"] for x in out if x["category_id"] == 0])


if __name__ == "__main__":
    main(sys.argv[1])
