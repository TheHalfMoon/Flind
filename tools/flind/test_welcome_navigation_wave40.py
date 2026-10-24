"""Exercise the actual Welcome API navigation logic without Django or DB."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
WELCOME = ROOT / "posthog/api/welcome.py"
LOADING = ROOT / "products/desktop/packages/ui/src/shell/AppLoadingScreen.tsx"
LOADING_TEST = ROOT / "products/desktop/packages/ui/src/shell/AppLoadingScreen.test.tsx"


def build_next_steps(user, products):
    parsed = ast.parse(WELCOME.read_text())
    func = next(
        node for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == "_build_suggested_next_steps"
    )
    source = compile(
        ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[])),
        str(WELCOME),
        "exec",
    )
    namespace = {"User": object, "_SUGGESTED_NEXT_STEPS_MAX_ITEMS": 3}
    exec(source, namespace)
    return namespace["_build_suggested_next_steps"](user, products)


class WelcomeNavigationWave40Tests(unittest.TestCase):
    def test_replay_and_experiments_keep_local_routes_without_vendor_docs(self):
        user = SimpleNamespace(role_at_organization="product", current_team_id=42)
        steps = build_next_steps(user, ["session_replay", "experiments"])
        self.assertEqual(
            [item["href"] for item in steps],
            ["/project/42/replay/home", "/project/42/experiments"],
        )
        self.assertTrue(all("docs_href" not in item for item in steps))

    def test_feature_flags_keep_local_route_without_external_link(self):
        user = SimpleNamespace(role_at_organization="engineering", current_team_id=91)
        steps = build_next_steps(user, ["feature_flags"])
        self.assertEqual(steps[0]["href"], "/project/91/feature_flags")
        self.assertNotIn("docs_href", steps[0])

    def test_empty_usage_preserves_local_home_fallback(self):
        user = SimpleNamespace(role_at_organization=None, current_team_id=None)
        steps = build_next_steps(user, [])
        self.assertEqual(steps[0]["href"], "/")
        self.assertEqual(steps[0]["label"], "Explore the project home")
        self.assertTrue(all(not item["href"].startswith(("https:", "http:")) for item in steps))

    def test_startup_loading_does_not_offer_inherited_external_support(self):
        component = LOADING.read_text()
        tests = LOADING_TEST.read_text()
        self.assertIn("Flind is taking longer than expected to start", component)
        self.assertIn('aria-label="Flind is starting"', component)
        self.assertIn("Support channel not configured", component)
        self.assertNotIn("EXTERNAL_LINKS.discord", component)
        self.assertNotIn("openExternalUrl", component)
        self.assertIn('name: "Get support"', tests)
        self.assertIn("toBeNull()", tests)


if __name__ == "__main__":
    unittest.main()
