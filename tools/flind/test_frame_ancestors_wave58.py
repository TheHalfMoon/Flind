"""Check Flind app iframe boundaries without Django app or DB imports."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CSP = ROOT / "posthog/csp_middleware.py"
INHERITED_TESTS = ROOT / "posthog/test/test_csp_middleware.py"


def frame_sources():
    tree = ast.parse(CSP.read_text())
    func = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "app_frame_ancestor_sources")
    namespace = {}
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=[func], type_ignores=[])
    ), str(CSP), "exec"), namespace)
    return namespace["app_frame_ancestor_sources"]()


class FrameAncestorsWave58Tests(unittest.TestCase):
    def test_no_inherited_external_iframe_ancestor(self):
        self.assertEqual(frame_sources(), [])

    def test_default_app_policy_is_self_only(self):
        source = CSP.read_text()
        self.assertIn('frame_ancestors = "frame-ancestors \'self\'"', source)
        self.assertNotIn('sources = ["https://posthog.com"', source)
        self.assertNotIn('https://preview.posthog.com', source)

    def test_shared_exporter_and_embedded_routes_remain_exempt(self):
        source = CSP.read_text()
        self.assertIn('if is_embeddable_document(request.path):', source)
        self.assertIn("csp_parts.remove(frame_ancestors)", source)
        for item in ('"/shared_dashboard/"', '"/embedded/"', '"/exporter/"'):
            self.assertIn(item, source)

    def test_admin_framing_remains_forbidden_without_vendor_exception(self):
        source = CSP.read_text()
        self.assertIn('"frame-ancestors \'none\'"', source)
        self.assertIn('"frame-src \'self\'"', source)
        self.assertNotIn('"frame-src https://posthog.com"', source)

    def test_original_inherited_integration_expectations_updated(self):
        source = INHERITED_TESTS.read_text()
        self.assertIn('assert enforced == "frame-ancestors \'self\'"', source)
        self.assertIn("test_html_response_has_no_inherited_csp_report_collector", source)
        self.assertNotIn("test_html_response_declares_default_reporting_endpoint_with_distinct_id", source)


if __name__ == "__main__":
    unittest.main()
