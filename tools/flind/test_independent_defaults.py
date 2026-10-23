"""Static safety gates for Flind-owned defaults and public metadata.

These checks deliberately avoid importing Django, SDKs, or network libraries.
They do not establish successful app startup or complete outbound isolation.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY = "post" + "hog"
OLD_CLOUD = "https://us." + LEGACY + ".com"
OLD_EU_CLOUD = "https://eu." + LEGACY + ".com"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class IndependentDefaultsTests(unittest.TestCase):
    def test_transactional_host_is_flind_own_origin(self):
        settings = read("posthog/settings/base_variables.py")
        sender = read("posthog/transactional_email.py")
        self.assertIn('FLIND_HOST: str = get_from_env("FLIND_HOST", get_from_env("SITE_URL", "http://localhost:8010"))', settings)
        self.assertNotIn(OLD_CLOUD, settings)
        self.assertIn("settings.FLIND_HOST", sender)
        self.assertNotIn("settings." + LEGACY.upper() + "_HOST", sender)

    def test_connect_origins_fail_closed_without_setup(self):
        settings = read("posthog/settings/integrations.py")
        for region in ("US", "EU"):
            self.assertIn('CONNECT_BASE_URL_' + region + '", "")', settings)
        self.assertNotIn(OLD_CLOUD, settings)
        self.assertNotIn(OLD_EU_CLOUD, settings)

    def test_openapi_servers_advertise_own_origin(self):
        web = read("posthog/settings/web.py")
        self.assertIn('{"url": os.getenv("SITE_URL", "http://localhost:8010").rstrip("/"), "description": "Flind instance"}', web)
        self.assertNotIn('"description": "PostHog Cloud', web)

    def test_temporal_ui_is_local_by_default(self):
        temporal = read("posthog/settings/temporal.py")
        self.assertIn('TEMPORAL_UI_HOST: str = os.getenv("TEMPORAL_UI_HOST", "http://localhost:8081")', temporal)
        self.assertNotIn('https://cloud.temporal.io', temporal)

    def test_public_metadata_is_only_flind(self):
        content = read("posthog/frontend_views.py")
        section = content[content.index("_PUBLIC_PAGE_METADATA"):content.index("def region_host_from_current_instance")]
        self.assertIn("Log in • Flind", section)
        self.assertIn("Sign up • Flind", section)
        self.assertNotIn(LEGACY.lower(), section.lower())
        self.assertNotIn("_PREVIEW_IMAGE_URL", section)
        self.assertIn('"name": "Flind"', section)

    def test_mobile_defaults_do_not_send_events_to_an_external_provider(self):
        env = read("products/desktop/apps/mobile/.env.example")
        mobile = read("products/desktop/apps/mobile/src/lib/flindAnalytics.ts")
        layout = read("products/desktop/apps/mobile/src/app/_layout.tsx")
        self.assertIn("EXPO_PUBLIC_FLIND_ANALYTICS_API_KEY=\n", env)
        self.assertIn("EXPO_PUBLIC_FLIND_ANALYTICS_HOST=\n", env)
        self.assertNotIn(OLD_CLOUD, env + mobile)
        self.assertNotIn("https://us.i." + LEGACY + ".com", env + mobile)
        self.assertIn('host: process.env.EXPO_PUBLIC_FLIND_ANALYTICS_HOST || "http://localhost:8010"', mobile)
        self.assertIn("FLIND_ANALYTICS_API_KEY && process.env.EXPO_PUBLIC_FLIND_ANALYTICS_HOST", layout)
        self.assertNotIn("sTMFPsFhdP1Ssg", env + mobile)


    def test_metrics_collector_uses_local_default(self):
        template = read("products/metrics/agent/config/config.yaml.tmpl")
        chart = read("products/metrics/agent/chart/posthog-metrics-agent/values.yaml")
        self.assertIn("http://localhost:8010", template)
        self.assertIn("http://localhost:8010", chart)
        self.assertNotIn("https://us.i." + LEGACY + ".com", template + chart)

    def test_desktop_admin_has_no_hardcoded_remote_auth_server(self):
        config = read("products/desktop/tools/announcements-admin/src/config.ts")
        self.assertIn("VITE_FLIND_HOST", config)
        self.assertIn("VITE_FLIND_OAUTH_CLIENT_ID", config)
        self.assertIn('http://localhost:8010', config)
        self.assertNotIn(LEGACY, config.lower())



    def test_admin_analytics_requires_explicit_key_and_host(self):
        src = read("products/desktop/tools/announcements-admin/src/analytics.ts")
        self.assertIn("VITE_FLIND_ANALYTICS_API_KEY", src)
        self.assertIn("VITE_FLIND_ANALYTICS_HOST", src)
        self.assertIn("if (!apiKey || !apiHost) return;", src)
        self.assertNotIn("VITE_" + LEGACY.upper() + "_API_HOST", src)

    def test_admin_package_is_flind_named(self):
        package = json.loads(read("products/desktop/tools/announcements-admin/package.json"))
        self.assertEqual(package["name"], "@flind/announcements-admin")



if __name__ == "__main__":
    unittest.main()
