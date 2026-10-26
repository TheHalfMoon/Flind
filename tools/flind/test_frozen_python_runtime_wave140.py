"""Wave140 regression tests for the exact frozen Python dependency qualifier."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.flind import qualify_frozen_python_runtime_wave140 as frozen


class FrozenPythonRuntimeWave140Tests(unittest.TestCase):
    def test_real_runtime_only_qualifies_python_packages(self):
        report = frozen.qualify()
        for key in (
            "django_app_registry_qualified", "django_migrations_qualified",
            "real_ingestion_and_dashboard_qualified", "tenant_isolation_qualified",
            "release_qualified",
        ):
            self.assertFalse(report[key])
        self.assertEqual(report["phase"], "exact-frozen-python-runtime")
        self.assertEqual(
            report["locked_python_runtime_qualified"],
            bool(report["python_exact_pin_passed"]
                 and report["django_import_passed"]
                 and report["django_exact_lock_version_passed"]
                 and report["direct_dependency_lock_passed"]),
        )

    def test_direct_lock_mismatch_fails_closed(self):
        actual = frozen.audit_runtime_lock()
        bad = {**actual, "direct_lock_qualified": False, "missing_count": 1}
        with patch.object(frozen, "audit_runtime_lock", return_value=bad):
            report = frozen.qualify()
        self.assertFalse(report["locked_python_runtime_qualified"])
        self.assertFalse(report["direct_dependency_lock_passed"])
        self.assertEqual(report["direct_dependency_counts"]["missing_count"], 1)

    def test_missing_lock_refuses_without_exception_details(self):
        with patch.object(frozen, "audit_runtime_lock", side_effect=ValueError("PRIVATE_TOKEN")):
            report = frozen.qualify()
        self.assertFalse(report["locked_python_runtime_qualified"])
        self.assertFalse(report["direct_dependency_lock_passed"])
        self.assertNotIn("PRIVATE_TOKEN", str(report))

    def test_negative_audit_counts_refuse(self):
        actual = frozen.audit_runtime_lock()
        bad = {**actual, "missing_count": -1}
        with patch.object(frozen, "audit_runtime_lock", return_value=bad):
            report = frozen.qualify()
        self.assertFalse(report["locked_python_runtime_qualified"])

    def test_sparse_checkout_never_implies_app_qualification(self):
        with patch.object(frozen, "source_is_full_checkout", return_value=False):
            report = frozen.qualify()
        self.assertFalse(report["full_source_checkout_available"])
        self.assertFalse(report["django_app_registry_qualified"])


if __name__ == "__main__":
    unittest.main()
