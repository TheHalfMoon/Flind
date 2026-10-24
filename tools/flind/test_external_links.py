"""Dependency-free behavioral tests for Flind's literal external-destination gate."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.flind.check_external_links import (
    audit_runtime_links,
    LEGACY_NAME,
    references_in_text,
    runtime_source,
)


class ExternalDestinationAuditTests(unittest.TestCase):
    def test_production_paths_only(self) -> None:
        self.assertTrue(runtime_source('frontend/src/scenes/billing/Billing.tsx'))
        self.assertTrue(runtime_source('products/desktop/apps/mobile/src/main.ts'))
        self.assertTrue(runtime_source(LEGACY_NAME + '/templates/signin.html'))
        for name in (
            'docs/launch.md', 'tools/flind/check_external_links.py',
            'frontend/src/lib/x.test.ts', 'frontend/src/lib/x.spec.tsx',
            LEGACY_NAME + '/test/test_api.py', 'products/foo/__tests__/a.ts',
            'frontend/src/generated/client.ts', 'frontend/node_modules/x.js',
            'LICENSE', 'frontend/src/a.json',
        ):
            with self.subTest(name=name):
                self.assertFalse(runtime_source(name))

    def test_recognizes_user_facing_legacy_links_and_mailboxes(self) -> None:
        text = """const a = 'https://{old}.com/docs/foo'
const b = 'http://us.{old}.com/api'
const c = 'mailto:sales@{old}.com?subject=Hi'
const d = 'https://www.{old}status.com/api/v1/summary'
const e = 'eu.{old}.com'
""".format(old=LEGACY_NAME)
        refs = references_in_text(text)
        self.assertEqual(len(refs), 5)
        self.assertEqual([x['kind'] for x in refs], ['url', 'url', 'email', 'url', 'host'])
        self.assertEqual([x['line'] for x in refs], [1, 2, 3, 4, 5])

    def test_does_not_mistake_lookalike_domains_for_legacy_hosts(self) -> None:
        text = """https://{old}.com.attacker.example/docs
https://not{old}.com/docs
https://flind.example/help
email@example-{old}.com
https://docs.example/{old}.com/help
""".format(old=LEGACY_NAME)
        self.assertEqual(references_in_text(text), [])

    def test_skips_duplicate_host_inside_full_links(self) -> None:
        refs = references_in_text(f'https://{LEGACY_NAME}.com/docs mailto:help@{LEGACY_NAME}.com')
        self.assertEqual(len(refs), 2)
        self.assertEqual([x['kind'] for x in refs], ['url', 'email'])

    def test_reads_only_tracked_runtime_source_and_reports_locations(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for name, content in {
                'frontend/src/help.tsx': f"export const dest = 'https://{LEGACY_NAME}.com/docs'\n",
                'services/sync/main.py': f"url = 'mailto:sales@{LEGACY_NAME}.com'\n",
                LEGACY_NAME + '/test/test_help.py': f"'https://{LEGACY_NAME}.com/docs'\n",
                'docs/README.md': f"https://{LEGACY_NAME}.com/docs\n",
                'frontend/src/x.spec.ts': f"https://{LEGACY_NAME}.com/docs\n",
            }.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            (root / 'frontend/src/untracked.ts').write_text(f'https://{LEGACY_NAME}.com/docs')
            subprocess.run(['git', 'add', 'frontend/src/help.tsx', 'services/sync/main.py',
                            LEGACY_NAME + '/test/test_help.py', 'docs/README.md', 'frontend/src/x.spec.ts'],
                           cwd=root, check=True)
            result = audit_runtime_links(root, sample_limit=1)
            self.assertEqual(result['candidate_source_files'], 2)
            self.assertEqual(result['inspected_source_files'], 2)
            self.assertEqual(result['files_with_legacy_destinations'], 2)
            self.assertEqual(result['legacy_destination_references'], 2)
            self.assertEqual(len(result['examples']), 1)
            self.assertFalse(result['literal_destination_gate_passed'])
            self.assertEqual(result['by_area'], {'frontend': 1, 'services': 1})
            strict = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('check_external_links.py')),
                 '--root', str(root), '--strict', '--sample-limit', '0'],
                capture_output=True, text=True,
            )
            self.assertEqual(strict.returncode, 2)
            self.assertEqual(json.loads(strict.stdout)['examples'], [])

    def test_oversized_runtime_source_cannot_pass_strict_gate(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            target = root / 'frontend/src/oversized.ts'
            target.parent.mkdir(parents=True)
            target.write_text('a' * 2_000_001)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            result = audit_runtime_links(root)
            self.assertFalse(result['literal_destination_gate_passed'])
            self.assertEqual(result['uninspected_source_files'][0]['reason'], 'size_limit')

    def test_no_destinations_pass_strict_gate(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            target = root / 'frontend/src/help.ts'
            target.parent.mkdir(parents=True)
            target.write_text('const help = "https://docs.flind.example";\n')
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            result = audit_runtime_links(root)
            self.assertTrue(result['literal_destination_gate_passed'])
            self.assertEqual(result['legacy_destination_references'], 0)


if __name__ == '__main__':
    unittest.main()
