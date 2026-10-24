"""Require the actual Diff parser source and safe optional MCP transport guard."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"products/desktop/apps/mobile/src"


class MobileTypeCleanupsWave34Tests(unittest.TestCase):
    def test_diff_block_imports_exported_local_parser(self):
        component=(BASE/"features/inbox/components/DiffBlock.tsx").read_text()
        source=(BASE/"features/inbox/activityLog.ts").read_text()
        self.assertIn('import { parseDiffLines } from "../activityLog";',component)
        self.assertIn("export function parseDiffLines(diff: string)",source)
        self.assertNotIn('@flind/core/inbox/activityLog',component)

    def test_optional_transport_check_accepts_generated_models(self):
        source=(BASE/"features/mcp/presentation.ts").read_text()
        self.assertIn("server: unknown",source)
        self.assertIn('typeof server === "object"',source)
        self.assertIn('"transport_type" in server',source)
        self.assertIn('server.transport_type === "stdio"',source)

    def test_native_behavior_test_covers_optional_fields(self):
        tests=(BASE/"features/mcp/presentation.test.ts").read_text()
        self.assertIn('{ transport_type: "stdio" }',tests)
        self.assertIn('{ transport_type: "sse" }',tests)
        self.assertIn("[null, false]",tests)


if __name__=="__main__":
    unittest.main()
