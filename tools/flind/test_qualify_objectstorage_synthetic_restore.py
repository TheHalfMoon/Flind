"""Fail-closed, offline regression for the ephemeral S3 recovery exercise."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.flind.qualify_objectstorage_synthetic_restore import (
    GuardError,
    require_runner_context,
    sha,
    verify_equal,
)

ROOT = Path(__file__).resolve().parents[2]


class SyntheticObjectRestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="flind-s3-test-")
        self.addCleanup(self.temporary.cleanup)
        self.env = {
            "GITHUB_ACTIONS": "true",
            "FLIND_SYNTHETIC_S3_RESTORE": "1",
            "DEBUG": "1",
            "DATABASE_URL": "postgres://posthog:posthog@localhost:5432/posthog",
            "FLIND_S3_ENDPOINT": "http://127.0.0.1:19000",
            "GITHUB_WORKSPACE": str(ROOT),
            "EVIDENCE": str(ROOT / "flind-evidence"),
            "RUNNER_TEMP": self.temporary.name,
            "GITHUB_RUN_ID": "43377771234",
            "GITHUB_RUN_ATTEMPT": "1",
        }

    def test_exact_ephemeral_dev_context_is_accepted_before_network(self) -> None:
        temp, evidence, bucket = require_runner_context(self.env, ROOT)
        self.assertEqual(temp, Path(self.temporary.name))
        self.assertEqual(evidence, ROOT / "flind-evidence")
        self.assertEqual(bucket, "flind-ci-restore-43377771234-1")

    def test_off_machine_or_wrong_context_fails_closed(self) -> None:
        variants = (
            ("GITHUB_ACTIONS", "false"),
            ("FLIND_SYNTHETIC_S3_RESTORE", "0"),
            ("FLIND_S3_ENDPOINT", "https://s3.amazonaws.com"),
            ("FLIND_S3_ENDPOINT", "http://localhost:19000"),
            ("FLIND_S3_ENDPOINT", "http://127.0.0.1:9000"),
            ("DATABASE_URL", "postgres://prod.invalid/production"),
            ("DEBUG", "0"),
            ("EVIDENCE", str(Path(self.temporary.name) / "foreign")),
            ("RUNNER_TEMP", "/not-an-ephemeral-runner-path"),
            ("GITHUB_RUN_ID", "not-a-real-id"),
            ("GITHUB_RUN_ATTEMPT", "invalid"),
            ("GITHUB_WORKSPACE", str(Path(self.temporary.name) / "other")),
        )
        for key, value in variants:
            with self.subTest(env_key=key):
                env = dict(self.env)
                env[key] = value
                with self.assertRaises(GuardError):
                    require_runner_context(env, ROOT)

    def test_wrong_working_directory_fails_before_any_s3_import(self) -> None:
        with self.assertRaisesRegex(GuardError, "workspace"):
            require_runner_context(self.env, Path(self.temporary.name))

    def test_byte_comparator_rejects_both_corruption_and_deletion(self) -> None:
        original = b"first\x00second\xff"
        verify_equal(original, original)
        for altered in (b"first-second\xff", b"first\x00", b""):
            with self.subTest(altered=altered):
                with self.assertRaises(AssertionError):
                    verify_equal(original, altered)
        self.assertEqual(len(sha(original)), 64)

    def test_owned_bucket_scope_and_no_untrusted_remote_endpoint(self) -> None:
        source = (ROOT / "tools/flind/qualify_objectstorage_synthetic_restore.py").read_text(encoding="utf-8")
        self.assertIn("bucket in names", source)
        self.assertIn('f"flind-ci-restore-{run_id}-{attempt}"', source)
        self.assertIn('endpoint_url="http://127.0.0.1:19000"', source)
        self.assertIn("created = False", source)
        self.assertIn("if created:", source)
        self.assertIn("client.delete_bucket(Bucket=bucket)", source)
        self.assertIn("synthetic object comparator failed to detect tampering", source)
        self.assertNotIn("list_objects_v2", source)
        self.assertNotIn("delete_objects(", source)


if __name__ == "__main__":
    unittest.main()
