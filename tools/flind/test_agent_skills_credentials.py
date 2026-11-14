"""Regression guard for inherited credentials in Flind agent-skills CI.

Run: python3 -m unittest tools.flind.test_agent_skills_credentials -v
No third-party packages, tokens, network, or Docker daemon required.
This guard is deliberately fail-closed until the workflow is remediated.
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ci-agent-skills.yml"

# Restrict this check to the workflow under review; the broader Actions
# credential inventory and release audit remain separate release blockers.
DONOR_CREDENTIALS = re.compile(
    r"(?i)(?:GH_APP_POSTHOG_[A-Z0-9_]+|DOCKERHUB_TOKEN|DOCKERHUB_USER)"
)
APP_TOKEN_ACTION = re.compile(
    r"(?im)^\s*-?\s*uses:\s*['\"]?actions/create-github-app-token@"
)
DOCKER_LOGIN_ACTION = re.compile(
    r"(?im)^\s*-?\s*uses:\s*['\"]?docker/login-action@"
)
SKIP_REVOCATION = re.compile(r"(?im)^\s*skip-token-revoke:\s*true\b")


class CredentialPatternTests(unittest.TestCase):
    def test_donor_secret_aliases_are_detected(self):
        for value in (
            "GH_APP_POSTHOG_SETUP_ACTIONS_PRIVATE_KEY",
            "GH_APP_POSTHOG_PATHS_FILTER_APP_ID",
            "DOCKERHUB_TOKEN",
            "DOCKERHUB_USER",
        ):
            with self.subTest(value=value):
                self.assertRegex(value, DONOR_CREDENTIALS)

    def test_quoted_action_references_are_detected(self):
        for value in (
            "- uses: actions/create-github-app-token@v3",
            "- uses: 'actions/create-github-app-token@v3'",
            '- uses: "docker/login-action@v4"',
            "- uses: docker/login-action@v4",
        ):
            with self.subTest(value=value):
                self.assertTrue(
                    APP_TOKEN_ACTION.search(value) or DOCKER_LOGIN_ACTION.search(value)
                )

    def test_unrelated_read_only_action_is_allowed(self):
        self.assertIsNone(APP_TOKEN_ACTION.search("- uses: actions/checkout@v4"))
        self.assertIsNone(DOCKER_LOGIN_ACTION.search("- uses: actions/checkout@v4"))

    def test_active_agent_skills_has_no_inherited_credentials(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIsNone(
            DONOR_CREDENTIALS.search(source),
            "Agent-skills workflow still references inherited donor credentials",
        )
        self.assertIsNone(
            APP_TOKEN_ACTION.search(source),
            "Agent-skills workflow still mints GitHub App tokens",
        )
        self.assertIsNone(
            DOCKER_LOGIN_ACTION.search(source),
            "Agent-skills workflow still performs registry login",
        )
        self.assertIsNone(
            SKIP_REVOCATION.search(source),
            "Agent-skills workflow still disables token revocation",
        )


if __name__ == "__main__":
    unittest.main()
