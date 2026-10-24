"""Guard lockfile ownership boundaries for external SDK dependencies."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
LOCK=ROOT/"products/desktop/pnpm-lock.yaml"
TICKET=ROOT/"products/desktop/apps/mobile/src/features/inbox/conversationsTicket.ts"
TICKET_TEST=ROOT/"products/desktop/apps/mobile/src/features/inbox/conversationsTicket.test.ts"


class DesktopSdkLockWave33Tests(unittest.TestCase):
    def test_published_sdk_transitive_dependencies_are_not_relabelled_as_flind_core(self):
        source=LOCK.read_text()
        self.assertNotRegex(source,re.compile(r"(?m)^      '@flind/core': 1\.60\.[0-9]+$"))
        snapshots=source.split("\nsnapshots:\n",1)[1]
        for name,version in (
            ("@posthog/browser-common", "1.60.1"),
            ("posthog-js","1.60.1"),
            ("posthog-node","1.60.0"),
            ("posthog-react-native","1.60.1"),
        ):
            start=re.search(r"(?m)^  '?"+re.escape(name)+r"@[^:\n]+:\n",snapshots)
            self.assertIsNotNone(start, name)
            rest=snapshots[start.end():]
            next_package=re.search(r"(?m)^  \S",rest)
            block=rest[:next_package.start()] if next_package else rest
            self.assertIn("'@posthog/core': "+version,block, name)
        self.assertIn("'@posthog/core@1.60.0':",source)
        self.assertIn("'@posthog/core@1.60.1':",source)

    def test_internal_flind_core_remains_workspace_dependency(self):
        source=LOCK.read_text()
        self.assertIn("'@flind/core':\n        specifier: workspace:*\n        version: link:../../packages/core",source)

    def test_support_ticket_hides_unconfigured_or_unsafe_links(self):
        source=TICKET.read_text()
        self.assertIn("getCloudUrlFromRegion(cloudRegion)",source)
        self.assertIn("catch {\n    return null;",source)
        tests=TICKET_TEST.read_text()
        self.assertIn("https://us.flind.example",tests)
        self.assertIn("EXPO_PUBLIC_FLIND_API_US_URL",tests)
        self.assertIn("does not generate a vendor link or crash",tests)
        self.assertIn("https://us.posthog.com",tests)


if __name__=="__main__":
    unittest.main()
