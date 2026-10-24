"""Regression checks for Mobile's typed session-event and MCP UI boundaries."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MOBILE = ROOT / "products/desktop/apps/mobile/src"


class MobileSharedTypeWave35Tests(unittest.TestCase):
    def test_mobile_events_reuse_portable_backend_contracts(self):
        source = (MOBILE / "features/tasks/types.ts").read_text()
        for name in (
            "PortableSessionEvent",
            "PortableSessionNotification",
            "CloudArtifactRef as CoreCloudArtifactRef",
        ):
            self.assertIn(name, source)
        for name in (
            "SessionEvent = PortableSessionEvent;",
            "SessionNotification = PortableSessionNotification;",
            "CloudArtifactRef = CoreCloudArtifactRef;",
        ):
            self.assertIn(name, source)
        self.assertIn("cloudArtifact?: CloudArtifactRef;", source)

    def test_mcp_host_uses_real_parser_fields_and_typed_csp(self):
        host = (MOBILE / "features/mcp/components/McpAppHost.tsx").read_text()
        self.assertNotIn("parsed.serverName", host)
        self.assertNotIn("parsed.toolName", host)
        self.assertIn("parsed.server", host)
        self.assertIn("parsed.tool", host)
        csp = (MOBILE / "features/mcp/mcpUiResource.ts").read_text()
        self.assertIn("csp?: McpUiResourceCsp", csp)
        self.assertNotIn("csp?: Record<string, unknown>", csp)

    def test_react_native_styles_use_exported_absolute_fill(self):
        for rel in (
            "features/navigation/components/NavDrawer.tsx",
            "features/mcp/components/McpAppHost.tsx",
            "features/tasks/composer/DotBackground.tsx",
        ):
            with self.subTest(file=rel):
                source = (MOBILE / rel).read_text()
                self.assertNotIn("StyleSheet.absoluteFillObject", source)
                self.assertIn("StyleSheet.absoluteFill", source)


if __name__ == "__main__":
    unittest.main()
