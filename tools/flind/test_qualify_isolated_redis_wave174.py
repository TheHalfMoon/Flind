"""Wave174 scratch Redis admission tests, no Django, no external sockets."""
from __future__ import annotations

from pathlib import Path
import socket
import tempfile
import unittest

from tools.flind.qualify_isolated_redis_wave174 import (
    MARKER, MARKER_TEXT, TEST_KEYS, admitted, qualify,
)


class RedisAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-redis174-", dir="/private/tmp")
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.redis = self.root / "redis"
        self.source.mkdir()
        self.redis.mkdir()
        (self.source / ".git").mkdir()
        (self.source / "pyproject.toml").write_text("name='flind'")
        (self.redis / MARKER).write_text(MARKER_TEXT)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(str(self.redis / "redis.sock"))

    def tearDown(self):
        self.sock.close()
        self.tmp.cleanup()

    def test_marked_private_tmp_unix_socket_admitted(self):
        self.assertTrue(admitted(self.source, self.redis, "HEAD"))
        self.assertTrue(admitted(self.source, self.redis, "ab" * 20))

    def test_marker_is_mandatory(self):
        (self.redis / MARKER).unlink()
        self.assertFalse(admitted(self.source, self.redis, "HEAD"))
        self.assertEqual(qualify(self.source, self.redis)["blocker"], "ValueError")

    def test_invalid_ref_and_no_first_party_checkout_refused(self):
        for ref in ("--upload-pack=bad", "../escape", "refs/../../other", ""):
            self.assertFalse(admitted(self.source, self.redis, ref))
        (self.source / "pyproject.toml").unlink()
        self.assertFalse(admitted(self.source, self.redis, "HEAD"))

    def test_symlinked_marker_refused(self):
        (self.redis / MARKER).unlink()
        target = self.root / "marker"
        target.write_text(MARKER_TEXT)
        (self.redis / MARKER).symlink_to(target)
        self.assertFalse(admitted(self.source, self.redis, "HEAD"))

    def test_non_socket_file_refused(self):
        self.sock.close()
        (self.redis / "redis.sock").unlink()
        (self.redis / "redis.sock").write_text("not a socket")
        self.assertFalse(admitted(self.source, self.redis, "HEAD"))

    def test_symlinked_redis_directory_refused(self):
        link = self.root / "linked"
        link.symlink_to(self.redis, target_is_directory=True)
        self.assertFalse(admitted(self.source, link, "HEAD"))

    def test_nested_redis_inside_source_refused(self):
        nested = self.source / "redis"
        nested.mkdir()
        (nested / MARKER).write_text(MARKER_TEXT)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as active:
            active.bind(str(nested / "redis.sock"))
            self.assertFalse(admitted(self.source, nested, "HEAD"))

    def test_product_release_gates_fail_closed_without_real_redis(self):
        (self.redis / MARKER).unlink()
        result = qualify(self.source, self.redis, ref="HEAD")
        for key in (
            "django_registry_qualified", "redis_direct_protocol_qualified",
            "django_cache_qualified", "expiration_qualified",
            "celery_worker_qualified", "tenant_auth_isolation_qualified",
            "ingestion_qualified", "release_qualified",
        ):
            self.assertFalse(result[key])
        self.assertTrue(all("synthetic" in name for name in TEST_KEYS))


if __name__ == "__main__":
    unittest.main()
