"""Fail-closed source guard for Flind metrics-agent CI distribution paths.

Run with: python3 -m unittest tools.flind.test_metrics_agent_no_publish -v
No third-party modules, Docker, network, secrets or external services.
The live-workflow test intentionally fails on main until the separate
metrics-agent test-only remediation is merged and qualified.
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/cd-metrics-agent-image.yml"

# Reject runnable publishing capabilities, not merely donor brand names.
FORBIDDEN = (
    re.compile(r"(?im)^\s*(?:packages\s*:\s*write|id-token\s*:\s*write)\s*(?:#.*)?$"),
    re.compile(r"(?im)^\s*-?\s*uses:\s*['\"]?(?:docker/login-action|docker/build-push-action)@"),
    re.compile(r"(?im)\b(?:docker\s+push|helm\s+push|docker\s+login)\b"),
    re.compile(r"(?im)\b(?:DOCKERHUB_TOKEN|DOCKERHUB_USER(?:NAME)?|GHCR_TOKEN)\b"),
    re.compile(r"(?im)\b(?:depot-ubuntu-[\w.-]+|depot\.dev)\b"),
    re.compile(r"(?im)^\s*(?:push|release|schedule|create|workflow_run)\s*:\s*(?:$|\S)"),
)
# workflow_dispatch is allowed only for manual test runs. A job must not
# upload artifacts to any registry even if the owner-specific guard is false.
REGISTRY_TARGET = re.compile(
    r"(?i)(?:ghcr\.io/(?:posthog|thehalfmoon)/|docker\.io/(?:posthog|thehalfmoon)/|oci://)"
)


def violations(source: str) -> list[str]:
    return [
        pattern.pattern
        for pattern in FORBIDDEN
        if pattern.search(source)
    ] + (["registry destination"] if REGISTRY_TARGET.search(source) else [])


class MetricsAgentNoPublishTests(unittest.TestCase):
    def test_active_workflow_is_test_only(self):
        self.assertTrue(WORKFLOW.is_file(), "missing active metrics-agent workflow")
        self.assertEqual([], violations(WORKFLOW.read_text(encoding="utf-8")))

    def test_rejects_docker_and_helm_push(self):
        self.assertTrue(violations("run: docker push ghcr.io/posthog/agent"))
        self.assertTrue(violations("run: helm push chart oci://registry/chart"))

    def test_rejects_inherited_secrets_and_privileged_permissions(self):
        self.assertTrue(violations("DOCKERHUB_TOKEN: ${{ secrets.DOCKERHUB_TOKEN }}"))
        self.assertTrue(violations("packages: write"))
        self.assertTrue(violations("id-token: write"))

    def test_rejects_external_runner_and_automatic_publish_triggers(self):
        self.assertTrue(violations("runs-on: depot-ubuntu-24.04"))
        self.assertTrue(violations("schedule:\n  - cron: '0 1 * * *'"))
        self.assertTrue(violations("push:\n  branches: [main]"))

    def test_allows_read_only_qualification(self):
        safe = """name: Flind metrics-agent tests
on:
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: helm lint products/metrics/agent/chart
"""
        self.assertEqual([], violations(safe))


if __name__ == "__main__":
    unittest.main()
