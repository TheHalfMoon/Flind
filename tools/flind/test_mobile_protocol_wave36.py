"""Wave 36: fail closed if incompatible mobile API and type contracts return."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "products/desktop"
MOBILE = DESKTOP / "apps/mobile/src"


class MobileProtocolWave36Tests(unittest.TestCase):
    def test_no_type_error_baseline_remains(self):
        baseline = json.loads((DESKTOP / "scripts/mobile-type-baseline.json").read_text())
        self.assertEqual(baseline["files"], {})

    def test_custom_mcp_auth_matches_supported_api_enum(self):
        ui = (MOBILE / "app/mcp-servers/add-custom.tsx").read_text()
        api = (DESKTOP / "packages/api-client/src/generated.ts").read_text()
        self.assertIn('MCPAuthTypeEnum = "api_key" | "oauth"', api)
        self.assertNotIn('{ value: "none", label: "None" }', ui)
        self.assertIn('useState<McpAuthType>("oauth")', ui)

    def test_legacy_github_integration_ids_are_checked_before_numeric_picker(self):
        helper = (MOBILE / "features/tasks/utils/repositorySelection.ts").read_text()
        hook = (MOBILE / "features/tasks/hooks/useIntegrations.ts").read_text()
        self.assertIn("normalizeLegacyGithubIntegrations", hook)
        self.assertIn("Number.isSafeInteger(id)", helper)
        self.assertIn("/^[1-9][0-9]*$/", helper)
        self.assertIn('item.kind !== "github"', helper)

    def test_cloud_permission_contract_and_platform_webview_are_explicit(self):
        permission = (DESKTOP / "packages/core/src/sessions/permissionResponse.ts").read_text()
        self.assertIn("CloudPermissionOption", permission)
        self.assertIn("PermissionOptionDisplay", permission)
        activity = (DESKTOP / "packages/core/src/sessions/sessionActivity.ts").read_text()
        self.assertIn('terminalStatus?: "failed" | "completed" | "stopped"', activity)
        host = (MOBILE / "features/mcp/components/McpAppHost.tsx").read_text()
        self.assertIn("IOSWebViewProps | AndroidWebViewProps", host)
        self.assertIn("MobilePlatformWebView", host)
        self.assertNotIn("as any", host)


if __name__ == "__main__":
    unittest.main()
