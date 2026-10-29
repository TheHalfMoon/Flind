"""Original first-party source/restore catalog comparison regression tests."""
from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

from .qualify_pg_restore_catalog_wave252 import (
    CatalogFormatError, compare_catalogs, normalize_rows, read_catalog,
)


class PostgresRestoredCatalogWave252(unittest.TestCase):
    @staticmethod
    def _catalog(*, compact: bool = False):
        key = "2" if compact else "3"
        return [
            ("relation", "public.synthetic_table", "r|p|false"),
            ("column", "public.synthetic_table.id", "1|integer|true||"),
            ("column", "public.synthetic_table.email", f"{key}|text|false||"),
            ("constraint", "public.synthetic_table.email_fk",
             f"f|true|true|true|{{{key}}}|{{1}}|synthetic_table"),
            ("index", "public.synthetic_email_idx",
             f"public.synthetic_table|true|false|true|{key}|1"),
        ]

    def test_dropped_column_attnums_are_normalized_by_column_name(self):
        actual = normalize_rows(self._catalog(compact=False))
        restored = normalize_rows(self._catalog(compact=True))
        report = compare_catalogs(actual, restored)
        self.assertTrue(report["canonical_catalog_equal"])
        self.assertEqual(report["differences"], 0)
        self.assertEqual(report["source_records"], 5)
        self.assertEqual(report["source_sha256"], report["restored_sha256"])
        self.assertFalse(report["release_qualified"])
        self.assertFalse(report["full_sql_expression_semantics_qualified"])

    def test_real_column_type_drift_is_not_normalized_away(self):
        source = normalize_rows(self._catalog())
        changed = [
            (kind, identity, "3|integer|false||" if identity.endswith(".email") else details)
            for kind, identity, details in self._catalog(compact=False)
        ]
        restored = normalize_rows(changed)
        self.assertFalse(compare_catalogs(source, restored)["canonical_catalog_equal"])

    def test_index_uniqueness_drift_is_not_normalized_away(self):
        source = normalize_rows(self._catalog())
        changed = [
            (kind, identity, details.replace("|true|false|true|", "|false|false|true|")
             if kind == "index" else details)
            for kind, identity, details in self._catalog()
        ]
        self.assertFalse(compare_catalogs(source, normalize_rows(changed))["canonical_catalog_equal"])

    def test_constraint_deferrability_drift_is_not_normalized_away(self):
        source = normalize_rows(self._catalog())
        changed = [
            (kind, identity, details.replace("f|true|true|true|", "f|false|true|true|")
             if kind == "constraint" else details)
            for kind, identity, details in self._catalog()
        ]
        self.assertFalse(compare_catalogs(source, normalize_rows(changed))["canonical_catalog_equal"])

    def test_unknown_attnum_is_refused(self):
        changed = [
            (kind, identity, detail.replace("|3|1", "|5|1") if kind == "index" else detail)
            for kind, identity, detail in self._catalog()
        ]
        with self.assertRaises(CatalogFormatError):
            normalize_rows(changed)

    def test_duplicate_identity_is_refused(self):
        rows = self._catalog()
        with self.assertRaises(CatalogFormatError):
            normalize_rows(rows + [rows[-1]])

    def test_extra_unrecognized_catalog_kind_is_refused(self):
        with self.assertRaises(CatalogFormatError):
            normalize_rows(self._catalog() + [("foreign", "public.synthetic", "whatever")])

    def test_csv_roundtrip_and_missing_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "first-party.csv"
            with file.open("w", newline="", encoding="utf-8") as out:
                csv.writer(out).writerows(self._catalog())
            report = compare_catalogs(read_catalog(file), normalize_rows(self._catalog()))
            self.assertTrue(report["canonical_catalog_equal"])
            with self.assertRaises(CatalogFormatError):
                read_catalog(Path(directory) / "absent.csv")

    def test_symlinked_snapshot_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_text("relation,public.synthetic,r|p|false\n")
            link = Path(directory) / "redirect.csv"
            link.symlink_to(source)
            with self.assertRaises(CatalogFormatError):
                read_catalog(link)

    def test_malformed_metadata_is_refused(self):
        bad = [("column", "public.synthetic.id", "not_an_attnum|text|true||")]
        with self.assertRaises(CatalogFormatError):
            normalize_rows(bad)


if __name__ == "__main__":
    unittest.main()
