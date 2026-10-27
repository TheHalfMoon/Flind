"""Wave176 tests for bounded synthetic-only Redis/Celery worker admission."""
from __future__ import annotations

from pathlib import Path
import socket
import tempfile
import unittest

from tools.flind.qualify_synthetic_celery_worker_wave176 import (
    ENV_REDIS, ENV_WORKER, QUEUE,
    REDIS_MARKER, REDIS_MARKER_CONTENT, WORKER_MARKER, WORKER_MARKER_CONTENT,
    build_app, qualify, validate_scratch,
)


class WorkerScratchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="flind-worker176-", dir="/private/tmp")
        self.base = Path(self.temp.name)
        self.redis_dir = self.base / "redis"
        self.worker_dir = self.base / "worker"
        self.redis_dir.mkdir()
        self.worker_dir.mkdir()
        (self.redis_dir / REDIS_MARKER).write_text(REDIS_MARKER_CONTENT)
        (self.worker_dir / WORKER_MARKER).write_text(WORKER_MARKER_CONTENT)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(str(self.redis_dir / "redis.sock"))

    def tearDown(self):
        self.sock.close()
        self.temp.cleanup()

    def test_only_marked_unix_scratch_is_admitted(self):
        self.assertTrue(validate_scratch(self.redis_dir, self.worker_dir))

    def test_missing_worker_marker_blocks_process_creation(self):
        (self.worker_dir / WORKER_MARKER).unlink()
        self.assertFalse(validate_scratch(self.redis_dir, self.worker_dir))
        result = qualify(self.redis_dir, self.worker_dir)
        self.assertEqual(result["blocker"], "ValueError")
        self.assertFalse(result["real_synthetic_worker_started"])
        self.assertFalse(result["release_qualified"])

    def test_missing_redis_marker_blocks_process_creation(self):
        (self.redis_dir / REDIS_MARKER).unlink()
        self.assertFalse(validate_scratch(self.redis_dir, self.worker_dir))

    def test_symlinked_worker_directory_refused(self):
        link = self.base / "link"
        link.symlink_to(self.worker_dir, target_is_directory=True)
        self.assertFalse(validate_scratch(self.redis_dir, link))

    def test_forged_unix_socket_regular_file_refused(self):
        self.sock.close()
        (self.redis_dir / "redis.sock").unlink()
        (self.redis_dir / "redis.sock").write_bytes(b"fake Redis Unix socket")
        self.assertFalse(validate_scratch(self.redis_dir, self.worker_dir))

    def test_scratch_dirs_must_be_separate(self):
        self.assertFalse(validate_scratch(self.redis_dir, self.redis_dir))

    def test_timeout_admission_fails_closed(self):
        for seconds in (0, 1, 7, 61, 1000):
            result = qualify(self.redis_dir, self.worker_dir, timeout=seconds)
            self.assertIn("blocker", result)
            self.assertFalse(result["synthetic_queue_roundtrip_qualified"])
            self.assertFalse(result["real_synthetic_worker_started"])

    def test_synthetic_task_registration_uses_own_queue_only(self):
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex
        original_create_connection = socket.create_connection
        try:
            app = build_app(self.redis_dir, self.worker_dir)
            self.assertEqual(app.conf.task_default_queue, QUEUE)
            self.assertEqual(app.tasks["flind.wave176.synthetic.echo"].run(73),
                             {"synthetic": True, "value": 73})
            self.assertIn("flind.wave176.synthetic.retry", app.tasks)
            self.assertTrue(app.conf.task_acks_late)
        finally:
            socket.socket.connect = original_connect
            socket.socket.connect_ex = original_connect_ex
            socket.create_connection = original_create_connection

    def test_release_and_tenant_flags_never_derive_from_synthetic_test(self):
        (self.redis_dir / REDIS_MARKER).unlink()
        result = qualify(self.redis_dir, self.worker_dir)
        for key in ("first_party_worker_qualified", "tenant_auth_isolation_qualified",
                    "ingestion_qualified", "release_qualified"):
            self.assertFalse(result[key])


if __name__ == "__main__":
    unittest.main()
