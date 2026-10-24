#!/usr/bin/env python3
"""Audit hardcoded inherited outbound link candidates in tracked Flind runtime source.

Read-only, standard-library only. A regex match is a source-review candidate,
NOT evidence of a request or browser navigation. This is separate from
the broad brand audit and from runtime network tracing.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE_EXTENSIONS = frozenset({
    '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.mts', '.cts',
    '.py', '.html', '.htm', '.ejs', '.jinja', '.jinja2',
    '.vue', '.svelte', '.rs', '.go',
})
MAX_SOURCE_BYTES = 2_000_000
LEGACY_NAME = 'post' + 'hog'
LEGACY_DOMAINS = rf'(?:{LEGACY_NAME}\.com|{LEGACY_NAME}status\.com)'
LEGACY_URL = re.compile(
    rf'(?i)\bhttps?://(?:[a-z0-9-]+\.)*{LEGACY_DOMAINS}'
    r'(?=$|[/:?#\s"\'\`<>])'
)
LEGACY_MAILTO = re.compile(
    rf'(?i)\bmailto:[a-z0-9._%+\-]+@(?:[a-z0-9-]+\.)*{LEGACY_NAME}\.com'
    r'(?=$|[?&#\s"\'\`<>])'
)
LEGACY_BARE_HOST = re.compile(
    rf'(?i)(?<![\w@./\-])(?:[a-z0-9-]+\.)*{LEGACY_DOMAINS}'
    r'(?=$|[/:?#\s"\'\`<>])'
)
PATTERNS = (("url", LEGACY_URL), ("email", LEGACY_MAILTO), ("host", LEGACY_BARE_HOST))


def runtime_source(path: str) -> bool:
    """Keep likely executable source; exclude reference/test/license documents."""
    parts = PurePosixPath(path).parts
    if not parts or PurePosixPath(path).suffix.lower() not in SOURCE_EXTENSIONS:
        return False
    if parts[0] in {'.github', '.depot', 'docs', 'tools', '.agents'}:
        return False
    if any(p.lower() in {
        'node_modules', 'vendor', 'vendored', 'fixtures', '__fixtures__',
        '__tests__', 'tests', 'test', 'snapshots', '__snapshots__',
        'generated', 'dist', 'build',
    } for p in parts[:-1]):
        return False
    name = parts[-1].lower()
    if (name.startswith('test_') or name.endswith(('.test.ts', '.test.tsx',
        '.spec.ts', '.spec.tsx', '.test.js', '.spec.js', '_test.py',
        '_test.go')) or name.startswith(('license', 'notice'))):
        return False
    return True


def tracked_sources(root: Path) -> list[str]:
    proc = subprocess.run(
        ['git', 'ls-files', '-z'], cwd=root, capture_output=True, check=True,
    )
    return sorted(
        raw.decode('utf-8', 'replace')
        for raw in proc.stdout.split(b'\0')
        if raw and runtime_source(raw.decode('utf-8', 'replace'))
    )


def references_in_text(source: str) -> list[dict[str, object]]:
    """Return nonoverlapping source matches with stable line numbers."""
    matches: list[tuple[int, dict[str, object]]] = []
    accepted: list[tuple[int, int]] = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(source):
            if any(match.start() < hi and match.end() > lo for lo, hi in accepted):
                continue
            accepted.append(match.span())
            matches.append((match.start(), {
                'kind': kind,
                'line': source.count('\n', 0, match.start()) + 1,
                'value': match.group(0),
            }))
    return [data for _, data in sorted(matches, key=lambda item: item[0])]


def audit_runtime_links(root: Path = ROOT, *, sample_limit: int = 50) -> dict[str, object]:
    if sample_limit < 0:
        raise ValueError('sample_limit must be nonnegative')
    files = tracked_sources(root)
    inspected = 0
    skipped: list[dict[str, str]] = []
    by_area: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    impacted_files = 0
    references = 0
    examples: list[dict[str, object]] = []
    for name in files:
        path = root / name
        try:
            if path.stat().st_size > MAX_SOURCE_BYTES:
                skipped.append({'path': name, 'reason': 'size_limit'})
                continue
            source = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            skipped.append({'path': name, 'reason': 'unreadable'})
            continue
        inspected += 1
        found = references_in_text(source)
        if not found:
            continue
        impacted_files += 1
        by_area[name.split('/', 1)[0]] += 1
        for item in found:
            references += 1
            by_type[str(item['kind'])] += 1
            if len(examples) < sample_limit:
                examples.append({'path': name, **item})
    return {
        'scope': 'Tracked probable runtime source; literal URL/mailto/host references only. Not proof of egress.',
        'candidate_source_files': len(files),
        'inspected_source_files': inspected,
        'uninspected_source_files': skipped,
        'files_with_legacy_destinations': impacted_files,
        'legacy_destination_references': references,
        'by_area': dict(sorted(by_area.items(), key=lambda x: (-x[1], x[0]))),
        'by_kind': dict(sorted(by_type.items())),
        'examples': examples,
        'literal_destination_gate_passed': references == 0 and not skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Git checkout to inspect')
    parser.add_argument('--sample-limit', type=int, default=50)
    parser.add_argument('--strict', action='store_true', help='exit 2 if matches or uninspected runtime source remain')
    args = parser.parse_args()
    data = audit_runtime_links(args.root.resolve(), sample_limit=args.sample_limit)
    print(json.dumps(data, indent=2, sort_keys=True))
    return 2 if args.strict and not data['literal_destination_gate_passed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
