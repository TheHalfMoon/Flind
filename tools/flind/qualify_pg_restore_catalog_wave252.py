#!/usr/bin/env python3
"""Fail-closed, offline PostgreSQL source/restore structural catalog comparison.

Input: two CSV streams produced by the identical read-only pg_catalog COPY
query in pg_restore_catalog_wave252.sql. Never connects to a database or
normalizes an expression's semantics. Physical attribute numbers may differ
after PostgreSQL pg_dump/pg_restore compacts dropped columns; compare index/
constraint keys by referenced column NAME instead.

Scope excludes CHECK expression semantics, index predicate/expression
semantics, user data, function bodies, and migration rollback. This is NOT
a release, bitwise backup, or full PostgreSQL recovery qualification.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

VALID_KINDS = frozenset({"relation", "column", "index", "constraint", "function", "trigger"})
MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_ROWS = 200_000
KEY_ARRAY = re.compile(r"\{[0-9]+(?:,[0-9]+)*\}\Z")
KEY_INDEX = re.compile(r"[0-9]+(?: [0-9]+)*\Z")


class CatalogFormatError(ValueError):
    """The input cannot be safely interpreted as a source catalog."""


def _resolve(raw: str, table: str, lookup: dict[tuple[str, int], str], *, index: bool) -> str:
    if not raw:
        return ""
    if index:
        if KEY_INDEX.fullmatch(raw) is None:
            raise CatalogFormatError("invalid index attnum sequence")
        numbers = raw.split(" ")
    else:
        if KEY_ARRAY.fullmatch(raw) is None:
            raise CatalogFormatError("invalid constraint attnum array")
        numbers = raw[1:-1].split(",")
    translated = []
    for text_num in numbers:
        number = int(text_num)
        if index and number == 0:
            translated.append("<expression>")
        elif number <= 0 or (table, number) not in lookup:
            raise CatalogFormatError("missing referenced column attnum")
        else:
            translated.append(lookup[(table, number)])
    return json.dumps(translated, ensure_ascii=False, separators=(",", ":"))


def normalize_rows(records: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    lookup: dict[tuple[str, int], str] = {}
    seen: set[tuple[str, str]] = set()
    for kind, identity, detail in records:
        if kind not in VALID_KINDS or not identity:
            raise CatalogFormatError("unknown catalog kind or empty identity")
        if (kind, identity) in seen:
            raise CatalogFormatError("duplicate catalog identity")
        seen.add((kind, identity))
        if kind != "column":
            continue
        if "." not in identity or "|" not in detail:
            raise CatalogFormatError("invalid column metadata")
        table, name = identity.rsplit(".", 1)
        number, rest = detail.split("|", 1)
        if not number.isdigit() or int(number) < 1 or rest.count("|") != 3:
            raise CatalogFormatError("invalid column physical attribute or type metadata")
        key = (table, int(number))
        if key in lookup:
            raise CatalogFormatError("duplicate physical column attribute")
        lookup[key] = name

    out: list[tuple[str, str, str]] = []
    for kind, identity, detail in records:
        if kind == "column":
            detail = detail.split("|", 1)[1]
        elif kind == "index":
            parts = detail.split("|")
            if len(parts) != 6 or "." not in parts[0]:
                raise CatalogFormatError("invalid index metadata")
            parts[4] = _resolve(parts[4], parts[0], lookup, index=True)
            detail = "|".join(parts)
        elif kind == "constraint" and detail:
            parts = detail.split("|")
            if len(parts) != 7 or "." not in identity:
                raise CatalogFormatError("invalid constraint metadata")
            owner = identity.rsplit(".", 1)[0]
            parts[4] = _resolve(parts[4], owner, lookup, index=False)
            referenced = "public." + parts[6]
            parts[5] = _resolve(parts[5], referenced, lookup, index=False)
            detail = "|".join(parts)
        out.append((kind, identity, detail))
    return sorted(out)


def read_catalog(path: Path) -> list[tuple[str, str, str]]:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_FILE_BYTES:
        raise CatalogFormatError("catalog file absent, redirected, empty, or too large")
    rows: list[tuple[str, str, str]] = []
    with path.open(newline="", encoding="utf-8") as source:
        for row in csv.reader(source, strict=True):
            if len(row) != 3:
                raise CatalogFormatError("expected three CSV fields: kind, identity, detail")
            rows.append((row[0], row[1], row[2]))
            if len(rows) > MAX_ROWS:
                raise CatalogFormatError("catalog row limit exceeded")
    if not rows:
        raise CatalogFormatError("empty catalog")
    return normalize_rows(rows)


def compare_catalogs(source: list[tuple[str, str, str]],
                     restored: list[tuple[str, str, str]]) -> dict:
    def digest(records: list[tuple[str, str, str]]) -> str:
        return hashlib.sha256(
            json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
    a = digest(source)
    b = digest(restored)
    kinds = dict(sorted(collections.Counter(kind for kind, _, _ in source).items()))
    equal = source == restored
    return {
        "source_sha256": a,
        "restored_sha256": b,
        "canonical_catalog_equal": equal,
        "source_records": len(source),
        "restored_records": len(restored),
        "source_kinds": kinds,
        "differences": sum(a != b for a, b in zip(source, restored))
                       + abs(len(source) - len(restored)),
        "full_sql_expression_semantics_qualified": False,
        "original_django_migrate_on_restored_db_qualified": False,
        "release_qualified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = compare_catalogs(read_catalog(args.source), read_catalog(args.restored))
    except (CatalogFormatError, UnicodeError, csv.Error, OSError) as error:
        print(json.dumps({"qualified": False, "error_class": type(error).__name__,
                          "release_qualified": False}), file=sys.stdout)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["canonical_catalog_equal"] else 2


if __name__ == "__main__":
    sys.exit(main())
