"""Self-hosted Flind must not direct users to a legacy vendor's cloud."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def source(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class CloudMigrationContainmentTests(unittest.TestCase):
    def test_legacy_route_is_safe_local_notice(self):
        scene = source("frontend/src/scenes/moveToPostHogCloud/MoveToPostHogCloud.tsx")
        self.assertIn("component: FlindCloudMigrationUnavailable", scene)
        self.assertIn("Flind Cloud migration is unavailable", scene)
        self.assertNotIn("https://", scene)
        self.assertNotIn("PostHog Cloud", scene)

    def test_account_dropdown_does_not_advertise_other_provider(self):
        account = source("frontend/src/lib/components/Account/AccountMenu.tsx")
        self.assertNotIn('top-menu-item-upgrade-to-cloud', account)
        self.assertNotIn('Try PostHog Cloud', account)
        self.assertNotIn('urls.moveToPostHogCloud()', account)

    def test_route_and_route_name_remain_consistent(self):
        # Retain existing bookmarked route as a compatibility alias.
        urls = source("frontend/src/scenes/urls.ts")
        scene_index = source("frontend/src/scenes/scenes.ts")
        self.assertIn("moveToPostHogCloud: (): string => '/move-to-cloud'", urls)
        self.assertIn("name: 'Flind Cloud migration unavailable'", scene_index)


if __name__ == "__main__":
    unittest.main()
