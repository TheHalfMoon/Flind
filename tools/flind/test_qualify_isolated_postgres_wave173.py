"""Wave173: tests for scratch-only PostgreSQL admission and migration selection."""
from __future__ import annotations
import os
import hashlib
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from tools.flind.qualify_isolated_postgres_wave173 import (
    PG_MARKER, PG_MARKER_TEXT, SOURCE_MARKER, SOURCE_MARKER_TEXT,
    SMOKE_APP, SMOKE_MIGRATION, execute, expected_migration, safe_locations,
    server_has_no_tcp_listeners, server_uses_only_approved_socket_dir,
    paths_are_pairwise_disjoint, has_pending_migration_plan,
    scratch_entrypoints_are_not_redirected, git_repository_entrypoints_are_isolated,
    is_supported_postgres_server_version, django_config_matches_private_postgres,
    smoke_migration_source_matches_commit, SMOKE_MIGRATION_PATH,
    SMOKE_MIGRATION_GIT_BLOB,
)
from tools.flind.qualify_sparse_django_registry_wave147 import git_offline_env


class CreateModel:
    def __init__(self, fields=None):
        self.fields = fields if fields is not None else [("id", SimpleNamespace(remote_field=None))]


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="flind-wave173-test-")
        self.base = Path(self.tmp.name)
        self.repo = self.base / "source"
        self.data = self.base / "pg"
        self.sock = self.base / "socket"
        for directory in (self.repo, self.data, self.sock):
            directory.mkdir()
        (self.repo / ".git").mkdir()
        (self.repo / ".git" / "objects").mkdir()
        (self.repo / "pyproject.toml").write_text("name='flind'")
        (self.repo / SOURCE_MARKER).write_text(SOURCE_MARKER_TEXT)
        (self.data / "PG_VERSION").write_text("17\n")
        (self.data / PG_MARKER).write_text(PG_MARKER_TEXT)
        (self.sock / ".s.PGSQL.65443").write_text("synthetic socket fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def test_refuses_any_cluster_outside_private_tmp(self):
        # Dedicated scratch data must be under /private/tmp on the actual Mac.
        self.assertFalse(safe_locations(
            self.repo, self.data, Path("/tmp"), 65443, "flind_wave173_synthetic"
        ))

    def test_invalid_database_and_port_rejected(self):
        self.assertFalse(safe_locations(self.repo, self.data, self.sock, 5432, "postgres"))
        self.assertFalse(safe_locations(self.repo, self.data, self.sock, 0, "flind_wave173_synthetic"))
        self.assertFalse(safe_locations(self.repo, self.data, self.sock, 65443, "user_customer_db"))

    def test_missing_dependency_receipt_names_only_safe_python_modules(self):
        # Fail before any Git, Django or PostgreSQL access. Do not emit the
        # arbitrary exception text, which can contain private paths or tokens.
        cases = (
            ("django.contrib.missing_flind_package",
             "django.contrib.missing_flind_package"),
            ("/private/tmp/credential=do_not_log", None),
            ("a" * 129, None),
            ("bad\\nmodule", None),
            (None, None),
        )
        for name, expected in cases:
            with self.subTest(name=name):
                error = ModuleNotFoundError(
                    "synthetic exception detail must not be in a receipt",
                    name=name,
                )
                with patch(
                    "tools.flind.qualify_isolated_postgres_wave173.safe_locations",
                    side_effect=error,
                ):
                    report = execute(
                        self.repo, "HEAD", self.data, self.sock, 65443,
                        "flind_wave173_synthetic", apply_rollback=True,
                    )
                self.assertEqual(report["blocker"], "ModuleNotFoundError")
                self.assertFalse(report["release_qualified"])
                self.assertFalse(report["one_first_party_apply_qualified"])
                if expected is None:
                    self.assertNotIn("missing_python_module", report)
                else:
                    self.assertEqual(report["missing_python_module"], expected)
                self.assertNotIn("synthetic exception detail", str(report))
                self.assertNotIn("credential=do_not_log", str(report))

    def test_scratch_marker_git_metadata_and_socket_redirections_refused(self):
        # Exercise the real production predicate on every entrypoint, without
        # requiring Windows symlink privileges or a live PostgreSQL instance.
        entries = (
            self.repo / SOURCE_MARKER, self.repo / ".git",
            self.repo / "pyproject.toml", self.data / PG_MARKER,
            self.data / "PG_VERSION", self.sock / ".s.PGSQL.65443",
        )
        self.assertTrue(scratch_entrypoints_are_not_redirected(
            self.repo, self.data, self.sock, 65443,
        ))
        for entry in entries:
            with self.subTest(entry=str(entry), redirect="symlink"):
                with patch.object(Path, "is_symlink", lambda path: path == entry):
                    self.assertFalse(scratch_entrypoints_are_not_redirected(
                        self.repo, self.data, self.sock, 65443,
                    ))
            with self.subTest(entry=str(entry), redirect="junction"):
                with patch.object(Path, "is_junction", lambda path: path == entry, create=True):
                    self.assertFalse(scratch_entrypoints_are_not_redirected(
                        self.repo, self.data, self.sock, 65443,
                    ))
        with patch.object(Path, "is_symlink", side_effect=OSError("synthetic")):
            self.assertFalse(scratch_entrypoints_are_not_redirected(
                self.repo, self.data, self.sock, 65443,
            ))

    def test_offline_git_reader_ignores_replace_refs_for_pinned_commit(self):
        # A real local Git replace ref can substitute a different commit's
        # tree without changing the SHA passed to rev-parse or cat-file.
        # Keep this regression entirely inside a disposable offline repo.
        repo = self.base / "replace-ref-repro"
        repo.mkdir()
        def git(*args, env=None):
            return subprocess.run(
                ["git", "-C", str(repo), *args],
                check=True, capture_output=True, env=env,
            ).stdout
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        with patch.dict(os.environ, clean_env, clear=True):
            git("init", "-q")
            git("config", "user.name", "Flind synthetic test")
            git("config", "user.email", "flind-test@example.invalid")
            source = repo / "synthetic.py"
            source.write_text("ORIGINAL = True\n", encoding="utf-8")
            git("add", "synthetic.py")
            git("commit", "-qm", "original")
            original = git("rev-parse", "HEAD").decode("ascii").strip()
            source.write_text("ORIGINAL = False\n", encoding="utf-8")
            git("add", "synthetic.py")
            git("commit", "-qm", "replacement")
            replacement = git("rev-parse", "HEAD").decode("ascii").strip()
            git("replace", original, replacement)
            self.assertEqual(
                git("show", original + ":synthetic.py"),
                b"ORIGINAL = False\n",
            )
            isolated = git_offline_env()
            self.assertEqual(isolated.get("GIT_NO_REPLACE_OBJECTS"), "1")
            self.assertEqual(isolated.get("GIT_NO_LAZY_FETCH"), "1")
            self.assertEqual(
                git("show", original + ":synthetic.py", env=isolated),
                b"ORIGINAL = True\n",
            )

    def test_git_repository_metadata_and_inherited_git_overrides_refused(self):
        # A .git file can point Git -C at a foreign checkout. Git environment
        # variables can override the selected repo even with a real .git dir.
        git_dir = self.repo / ".git"
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(git_repository_entrypoints_are_isolated(self.repo))
            for entry in (
                git_dir / "commondir",
                git_dir / "objects" / "info" / "alternates",
            ):
                with self.subTest(entry=str(entry)):
                    entry.parent.mkdir(parents=True, exist_ok=True)
                    entry.write_text("../foreign")
                    self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
                    entry.unlink()
            with patch.object(Path, "is_junction",
                              lambda path: path == git_dir, create=True):
                self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
            git_dir.rename(self.repo / ".git-backup")
            git_dir.write_text("gitdir: /private/tmp/foreign/.git\n")
            self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
            git_dir.unlink()
            (self.repo / ".git-backup").rename(git_dir)
            self.assertTrue(git_repository_entrypoints_are_isolated(self.repo))
        for key in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG_GLOBAL",
                    "GIT_WORK_TREE"):
            with self.subTest(key=key), patch.dict(
                os.environ, {key: "/private/tmp/foreign"}, clear=True,
            ):
                self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))

    def test_git_object_store_and_control_path_redirections_refused(self):
        # A real git -C checkout can read foreign objects when .git/objects
        # points elsewhere; alternates need not exist. Test both alias types.
        git_dir = self.repo / ".git"
        entries = (
            git_dir / "objects", git_dir / "HEAD", git_dir / "config",
            git_dir / "packed-refs", git_dir / "refs", git_dir / "objects" / "info",
            git_dir / "objects" / "pack",
        )
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(git_repository_entrypoints_are_isolated(self.repo))
            for entry in entries:
                with self.subTest(entry=str(entry), alias="symlink"):
                    with patch.object(Path, "is_symlink", lambda path: path == entry):
                        self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
                with self.subTest(entry=str(entry), alias="junction"):
                    with patch.object(Path, "is_junction",
                                      lambda path: path == entry, create=True):
                        self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
            if os.name != "nt":
                with tempfile.TemporaryDirectory(prefix="flind-foreign-objects-") as temp:
                    foreign = Path(temp) / "objects"
                    foreign.mkdir()
                    objects = git_dir / "objects"
                    backup = git_dir / "objects-backup"
                    objects.rename(backup)
                    try:
                        objects.symlink_to(foreign, target_is_directory=True)
                        self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
                    finally:
                        if objects.is_symlink():
                            objects.unlink()
                        backup.rename(objects)
            self.assertTrue(git_repository_entrypoints_are_isolated(self.repo))
            if os.name != "nt":
                # Git follows a packed-refs symlink and can read foreign refs.
                foreign_refs = self.base / "foreign-packed-refs"
                foreign_refs.write_text("# synthetic packed refs fixture\n")
                packed_refs = git_dir / "packed-refs"
                packed_refs.symlink_to(foreign_refs)
                try:
                    self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
                finally:
                    packed_refs.unlink()

    def test_nested_git_refs_cannot_redirect_a_commit_to_foreign_checkout(self):
        # Git rev-parse follows a loose ref symlink even when .git/refs and
        # .git/objects are local, defeating a check on the top-level dirs.
        # Mock the link kind so this regression runs without Windows privilege.
        refs = self.repo / ".git" / "refs"
        heads = refs / "heads"
        heads.mkdir(parents=True)
        branch = heads / "main"
        branch.write_text("a" * 40 + "\n")
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(git_repository_entrypoints_are_isolated(self.repo))
            for entry in (heads, branch):
                for kind in ("is_symlink", "is_junction"):
                    with self.subTest(entry=str(entry), alias=kind):
                        with patch.object(
                            Path, kind, lambda path, target=entry: path == target,
                            create=True,
                        ):
                            self.assertFalse(
                                git_repository_entrypoints_are_isolated(self.repo)
                            )
            if os.name != "nt":
                foreign = self.base / "foreign-commit-ref"
                foreign.write_text("b" * 40 + "\n")
                branch.unlink()
                branch.symlink_to(foreign)
                try:
                    self.assertFalse(git_repository_entrypoints_are_isolated(self.repo))
                finally:
                    branch.unlink()

    def test_individual_git_pack_index_and_loose_object_aliases_refused(self):
        # Git can load foreign commits through symlinked pack and idx files,
        # even when .git/objects and pack/ are real local directories.
        store = self.repo / ".git" / "objects"
        cases = (
            "pack/pack-flind-fixture.pack",
            "pack/pack-flind-fixture.idx",
            "ab/" + "0" * 38,
        )
        with patch.dict(os.environ, {}, clear=True):
            for relative in cases:
                entry = store / relative
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.write_bytes(b"owned synthetic object fixture")
                self.assertTrue(git_repository_entrypoints_are_isolated(self.repo))
                for kind in ("is_symlink", "is_junction"):
                    with self.subTest(relative=relative, redirect=kind):
                        with patch.object(
                            Path, kind, lambda path: path == entry, create=True,
                        ):
                            self.assertFalse(
                                git_repository_entrypoints_are_isolated(self.repo)
                            )
                if os.name != "nt":
                    foreign = self.base / "foreign-object-fixture"
                    foreign.write_bytes(b"foreign synthetic object fixture")
                    entry.unlink()
                    entry.symlink_to(foreign)
                    try:
                        self.assertFalse(
                            git_repository_entrypoints_are_isolated(self.repo)
                        )
                    finally:
                        entry.unlink()
                else:
                    entry.unlink()
            self.assertTrue(git_repository_entrypoints_are_isolated(self.repo))

    def test_missing_marker_fails_closed_before_django_import(self):
        (self.data / PG_MARKER).unlink()
        self.assertFalse(safe_locations(
            self.repo, self.data, self.sock, 65443, "flind_wave173_synthetic"
        ))
        report = execute(self.repo, "HEAD", self.data, self.sock, 65443,
                         "flind_wave173_synthetic", apply_rollback=True)
        self.assertEqual(report["blocker"], "ValueError")
        self.assertFalse(report["postgres_readonly_connection_qualified"])
        self.assertFalse(report["postgres_tcp_disabled_qualified"])
        self.assertFalse(report["postgres_socket_directory_qualified"])
        self.assertFalse(report["postgres_version_qualified"])
        self.assertFalse(report["one_first_party_apply_qualified"])
        self.assertFalse(report["release_qualified"])

    def test_canonical_django_private_postgres_settings_are_accepted(self):
        # Real Flind posthog/settings/data_stores.py configures HOST/PORT at
        # top-level via dj_database_url.config(), not under OPTIONS.
        expected = {
            "NAME": "flind_wave173_synthetic",
            "HOST": str(self.sock),
            "PORT": "65443",
            "OPTIONS": {"options": "-c lock_timeout=20000"},
        }
        self.assertTrue(django_config_matches_private_postgres(
            expected, "flind_wave173_synthetic", self.sock, 65443,
        ))
        self.assertTrue(django_config_matches_private_postgres(
            {**expected, "PORT": 65443, "OPTIONS": {}},
            "flind_wave173_synthetic", self.sock, 65443,
        ))
        self.assertTrue(django_config_matches_private_postgres(
            {**expected, "OPTIONS": {
                "host": str(self.sock), "port": "65443",
            }}, "flind_wave173_synthetic", self.sock, 65443,
        ))

    def test_libpq_options_cannot_redirect_before_server_side_verification(self):
        # Django forwards OPTIONS into the initial psycopg/libpq connection.
        # Admission must reject overrides before opening any DB cursor.
        expected = {
            "NAME": "flind_wave173_synthetic",
            "HOST": str(self.sock),
            "PORT": "65443",
            "OPTIONS": {},
        }
        for key, value in (
            ("dbname", "foreign_db"), ("database", "foreign_db"),
            ("hostaddr", "127.0.0.1"), ("service", "foreign_service"),
            ("servicefile", "/tmp/foreign_service"), ("passfile", "/tmp/foreign_pass"),
            ("user", "foreign_role"), ("password", "foreign_secret"),
            ("sslmode", "verify-full"), ("replication", "database"),
            ("target_session_attrs", "read-write"),
        ):
            with self.subTest(connection_override=key):
                self.assertFalse(django_config_matches_private_postgres(
                    {**expected, "OPTIONS": {key: value}},
                    "flind_wave173_synthetic", self.sock, 65443,
                ))
        for startup_options in (
            "-c lock_timeout=0",
            "-c search_path=foreign",
            "-c lock_timeout=20000 -c search_path=foreign",
            "-c lock_timeout=5000",
        ):
            with self.subTest(startup_options=startup_options):
                self.assertFalse(django_config_matches_private_postgres(
                    {**expected, "OPTIONS": {"options": startup_options}},
                    "flind_wave173_synthetic", self.sock, 65443,
                ))
        # Original source-audited 20-second lock timeout remains supported.
        self.assertTrue(django_config_matches_private_postgres(
            {**expected, "OPTIONS": {
                "host": str(self.sock), "port": 65443,
                "options": "-c lock_timeout=20000",
            }},
            "flind_wave173_synthetic", self.sock, 65443,
        ))

    def test_django_database_url_query_socket_options_without_top_level_host_port(self):
        # This is the actual shape returned by dj_database_url.parse() for
        # postgres://user@/db?host=/private/tmp/.../socket&port=65443.
        # Empty top-level fields must not override the exact private socket
        # and port supplied by canonical OPTIONS.
        canonical = {
            "NAME": "flind_wave173_synthetic",
            "HOST": "",
            "PORT": "",
            "OPTIONS": {"host": str(self.sock), "port": 65443},
        }
        self.assertTrue(django_config_matches_private_postgres(
            canonical, "flind_wave173_synthetic", self.sock, 65443,
        ))
        # Every location must still be pinned; never accept an absent,
        # external, or contradictory top-level/OPTIONS target.
        mutations = (
            {**canonical, "OPTIONS": {"port": 65443}},
            {**canonical, "OPTIONS": {"host": str(self.sock)}},
            {**canonical, "OPTIONS": {}},
            {**canonical, "HOST": "localhost"},
            {**canonical, "HOST": "/private/tmp/foreign"},
            {**canonical, "PORT": "5432"},
            {**canonical, "OPTIONS": {"host": "/private/tmp/foreign", "port": 65443}},
            {**canonical, "OPTIONS": {"host": str(self.sock), "port": 5432}},
            {**canonical, "OPTIONS": {
                "host": str(self.sock), "port": 65443, "dbname": "foreign",
            }},
        )
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                self.assertFalse(django_config_matches_private_postgres(
                    candidate, "flind_wave173_synthetic", self.sock, 65443,
                ))

    def test_django_host_port_or_options_override_mismatch_is_refused(self):
        expected = {
            "NAME": "flind_wave173_synthetic",
            "HOST": str(self.sock),
            "PORT": "65443",
            "OPTIONS": {},
        }
        mutations = (
            {**expected, "NAME": "foreign_db"},
            {**expected, "HOST": "localhost"},
            {**expected, "HOST": ""},
            {**expected, "HOST": "/private/tmp/foreign"},
            {**expected, "PORT": "5432"},
            {**expected, "PORT": "oops"},
            {**expected, "OPTIONS": {"host": "localhost"}},
            {**expected, "OPTIONS": {"host": "/private/tmp/foreign"}},
            {**expected, "OPTIONS": {"port": 5432}},
            {**expected, "OPTIONS": {"port": "invalid"}},
            {**expected, "OPTIONS": None},
            {**expected, "OPTIONS": []},
        )
        for invalid in mutations:
            with self.subTest(invalid=invalid):
                self.assertFalse(django_config_matches_private_postgres(
                    invalid, "flind_wave173_synthetic", self.sock, 65443,
                ))

    def test_supported_pg_version_is_17_9_or_newer_on_major_17_only(self):
        self.assertTrue(is_supported_postgres_server_version("170009"))
        self.assertTrue(is_supported_postgres_server_version(170010))
        self.assertTrue(is_supported_postgres_server_version("179999"))
        for rejected in (None, "", "17.9", "garbage", 170008, 170000, 160022,
                         180000, 190000, 0, -1, float("inf")):
            with self.subTest(version=rejected):
                self.assertFalse(is_supported_postgres_server_version(rejected))

    def test_rejects_every_tcp_listener_even_loopback(self):
        # The client using a Unix socket does NOT prove the server has
        # no concurrent TCP listeners. The PostgreSQL setting must be empty.
        self.assertTrue(server_has_no_tcp_listeners(""))
        for listen_addresses in (
            "localhost", "127.0.0.1", "::1", "0.0.0.0", "*",
            "127.0.0.1,::1", " ", None,
        ):
            with self.subTest(listen_addresses=listen_addresses):
                self.assertFalse(server_has_no_tcp_listeners(listen_addresses))

    def test_refusal_result_does_not_claim_postgres_tcp_is_disabled(self):
        # No marked PostgreSQL cluster means no right to claim TCP isolation.
        (self.data / PG_MARKER).unlink()
        report = execute(self.repo, "HEAD", self.data, self.sock, 65443,
                         "flind_wave173_synthetic", apply_rollback=True)
        self.assertFalse(report["postgres_tcp_disabled_qualified"])
        self.assertFalse(report["postgres_socket_directory_qualified"])
        self.assertFalse(report["postgres_version_qualified"])
        self.assertFalse(report["one_first_party_apply_qualified"])
        self.assertFalse(report["release_qualified"])

    def test_socket_api_restored_after_late_source_reader_failure(self):
        # A real exception after installing the deny-TCP monkeypatch must
        # not poison the socket API of subsequent tests or library callers.
        fake = ModuleType("tools.flind.qualify_sparse_django_registry_wave147")
        fake.index_tracked_python = lambda *_args: []
        fake.graph_source_ready = lambda *_args: (True, 1)
        fake.git_offline_env = lambda: dict(os.environ)

        class FailingGitBlobBatchReader:
            def __init__(self, *_args):
                pass

            def __enter__(self):
                current_api = (
                    socket.socket.connect, socket.socket.connect_ex,
                    socket.create_connection,
                )
                if any(current is original for current, original in zip(current_api, original_api)):
                    raise AssertionError("socket_policy_not_installed_before_reader")
                raise RuntimeError("synthetic_reader_failure")

            def __exit__(self, *_args):
                return False

        fake.GitBlobBatchReader = FailingGitBlobBatchReader
        fake.GitTrackedPythonFinder = object
        original_api = (
            socket.socket.connect, socket.socket.connect_ex,
            socket.create_connection,
        )
        with (
            patch.dict(sys.modules, {fake.__name__: fake}),
            patch("tools.flind.qualify_isolated_postgres_wave173.safe_locations", return_value=True),
            patch("tools.flind.qualify_isolated_postgres_wave173.subprocess.run",
                  return_value=SimpleNamespace(returncode=0, stdout=b"f" * 40)),
            patch("tools.flind.qualify_isolated_postgres_wave173.signal.alarm", create=True,
                  return_value=0) as alarm,
            patch.object(sys, "path", list(sys.path)),
            patch.dict(os.environ, {}, clear=False),
        ):
            report = execute(
                self.repo, "HEAD", self.data, self.sock, 65443,
                "flind_wave173_synthetic", apply_rollback=True,
            )
        self.assertEqual(report["blocker"], "RuntimeError")
        self.assertEqual([call.args[0] for call in alarm.call_args_list], [150, 0])
        self.assertFalse(report["postgres_tcp_disabled_qualified"])
        self.assertFalse(report["postgres_socket_directory_qualified"])
        self.assertFalse(report["postgres_version_qualified"])
        self.assertFalse(report["one_first_party_apply_qualified"])
        self.assertEqual(
            (socket.socket.connect, socket.socket.connect_ex, socket.create_connection),
            original_api,
        )

    def test_resolved_git_index_is_executable_ast_not_commented_out(self):
        # Literal backslash-n in a comment once swallowed the entire tracked
        # assignment, so source-text substring checks would give a false PASS.
        import ast
        import inspect
        import textwrap

        tree = ast.parse(textwrap.dedent(inspect.getsource(execute)))
        indexed = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "tracked"
                    for target in node.targets)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "index_tracked_python"
            and len(node.value.args) == 2
            and all(isinstance(arg, ast.Name) and arg.id == expected
                    for arg, expected in zip(node.value.args, ("root", "sha")))
        ]
        self.assertEqual(len(indexed), 1)

    def test_all_git_source_readers_use_resolved_commit_not_moving_ref(self):
        # A branch can move between rev-parse, ls-tree and cat-file.
        # All three first-party source readers must use the immutable SHA.
        resolved_sha = "a" * 40
        seen = []
        source = ModuleType("tools.flind.qualify_sparse_django_registry_wave147")

        def index_source(_root, ref):
            seen.append(("index", ref))
            return set()

        def make_finder(_root, ref, _tracked, **_kwargs):
            seen.append(("finder", ref))
            return object()

        class Reader:
            def __init__(self, _root, ref):
                seen.append(("reader", ref))

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        source.index_tracked_python = index_source
        source.graph_source_ready = lambda *_args: (True, 1)
        source.git_offline_env = lambda: dict(os.environ)
        source.GitBlobBatchReader = Reader
        source.GitTrackedPythonFinder = make_finder
        django = ModuleType("django")

        def fail_django_setup():
            raise RuntimeError("synthetic_django_import_refusal")

        django.setup = fail_django_setup
        with (
            patch.dict(sys.modules, {source.__name__: source, "django": django}),
            patch("tools.flind.qualify_isolated_postgres_wave173.safe_locations",
                  return_value=True),
            patch("tools.flind.qualify_isolated_postgres_wave173.subprocess.run",
                  return_value=SimpleNamespace(
                      returncode=0, stdout=resolved_sha.encode("ascii"),
                  )),
            patch("tools.flind.qualify_isolated_postgres_wave173.signal.alarm", create=True,
                  return_value=0),
        ):
            report = execute(
                self.repo, "moving-branch", self.data, self.sock, 65443,
                "flind_wave173_synthetic", apply_rollback=True,
            )
        self.assertEqual(report["source_commit"], resolved_sha)
        self.assertEqual(report["blocker"], "RuntimeError")
        self.assertEqual(seen, [
            ("index", resolved_sha),
            ("reader", resolved_sha),
            ("finder", resolved_sha),
        ])
        self.assertFalse(report["one_first_party_apply_qualified"])

    def test_process_state_restored_after_late_django_failure(self):
        # No imported finder, synthetic service URL or sys.path edits may leak
        # into a caller after the original qualifier has installed its policy.
        fake_source = ModuleType("tools.flind.qualify_sparse_django_registry_wave147")
        fake_source.index_tracked_python = lambda *_args: []
        fake_source.graph_source_ready = lambda *_args: (True, 1)
        fake_source.git_offline_env = lambda: dict(os.environ)
        finder = object()
        fake_source.GitTrackedPythonFinder = lambda *_args, **_kwargs: finder

        class Reader:
            def __init__(self, *_args):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        fake_source.GitBlobBatchReader = Reader
        fake_django = ModuleType("django")

        def fail_setup():
            raise RuntimeError("synthetic_late_django_failure")

        fake_django.setup = fail_setup
        original_path = list(sys.path)
        original_meta_path = list(sys.meta_path)
        env_keys = (
            "DJANGO_SETTINGS_MODULE", "SECRET_KEY", "DATABASE_URL",
            "POSTHOG_DB_NAME", "PGHOST", "PGPORT", "PGDATABASE",
            "REDIS_URL", "CLICKHOUSE_HOST", "CLICKHOUSE_PORT",
            "KAFKA_HOSTS", "PYTHONDONTWRITEBYTECODE", "DISABLE_MMDB",
        )
        original_env = {key: os.environ.get(key) for key in env_keys}
        with (
            patch.dict(sys.modules, {
                fake_source.__name__: fake_source, "django": fake_django,
            }),
            patch("tools.flind.qualify_isolated_postgres_wave173.safe_locations",
                  return_value=True),
            patch("tools.flind.qualify_isolated_postgres_wave173.subprocess.run",
                  return_value=SimpleNamespace(returncode=0, stdout=b"f" * 40)),
            patch("tools.flind.qualify_isolated_postgres_wave173.signal.alarm", create=True, return_value=0),
            patch.object(sys, "path", list(sys.path)),
            patch.dict(os.environ, {}, clear=False),
        ):
            report = execute(
                self.repo, "HEAD", self.data, self.sock, 65443,
                "flind_wave173_synthetic", apply_rollback=True,
            )
            self.assertEqual(sys.path, original_path)
            self.assertEqual(sys.meta_path, original_meta_path)
            self.assertNotIn(finder, sys.meta_path)
            self.assertEqual(
                {key: os.environ.get(key) for key in env_keys}, original_env
            )
        self.assertEqual(report["blocker"], "RuntimeError")
        self.assertFalse(report["postgres_tcp_disabled_qualified"])
        self.assertFalse(report["postgres_socket_directory_qualified"])
        self.assertFalse(report["postgres_version_qualified"])
        self.assertFalse(report["one_first_party_apply_qualified"])
        self.assertFalse(report["release_qualified"])

    def test_isolated_connection_closed_after_django_config_refusal(self):
        # Once Django returns a connection, even a rejected configuration
        # must close it before the global Unix-only socket policy is lifted.
        from unittest.mock import Mock

        source = ModuleType("tools.flind.qualify_sparse_django_registry_wave147")
        source.index_tracked_python = lambda *_args: []
        source.graph_source_ready = lambda *_args: (True, 1)
        source.git_offline_env = lambda: dict(os.environ)
        source.GitTrackedPythonFinder = lambda *_args, **_kwargs: object()

        class Reader:
            def __init__(self, *_args):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        source.GitBlobBatchReader = Reader
        django = ModuleType("django")
        django.setup = lambda: None
        apps_module = ModuleType("django.apps")
        apps_module.apps = SimpleNamespace(get_app_configs=lambda: ["synthetic"])
        db_module = ModuleType("django.db")
        connection = SimpleNamespace(
            settings_dict={"NAME": "foreign_db", "OPTIONS": {
                "host": str(self.sock), "port": 65443,
            }},
            close=Mock(),
        )
        db_module.connections = {"default": connection}
        migrations = ModuleType("django.db.migrations")
        executor_module = ModuleType("django.db.migrations.executor")
        executor_module.MigrationExecutor = object

        modules = {
            source.__name__: source, "django": django,
            apps_module.__name__: apps_module, db_module.__name__: db_module,
            migrations.__name__: migrations,
            executor_module.__name__: executor_module,
        }
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex
        original_create_connection = socket.create_connection

        # Never assert *inside* close(): the qualifier deliberately catches
        # close exceptions and preserves the original blocker. Capture the
        # observation and assert it after execute() has returned instead.
        close_observation = {}

        def close_inside_isolation_policy():
            close_observation["isolated"] = all((
                socket.socket.connect is not original_connect,
                socket.socket.connect_ex is not original_connect_ex,
                socket.create_connection is not original_create_connection,
            ))

        connection.close.side_effect = close_inside_isolation_policy
        with (
            patch.dict(sys.modules, modules),
            patch("tools.flind.qualify_isolated_postgres_wave173.safe_locations",
                  return_value=True),
            patch("tools.flind.qualify_isolated_postgres_wave173.subprocess.run",
                  return_value=SimpleNamespace(returncode=0, stdout=b"f" * 40)),
            patch("tools.flind.qualify_isolated_postgres_wave173.signal.alarm", create=True, return_value=0),
            patch.object(sys, "path", list(sys.path)),
            patch.dict(os.environ, {}, clear=False),
        ):
            report = execute(
                self.repo, "HEAD", self.data, self.sock, 65443,
                "flind_wave173_synthetic", apply_rollback=True,
            )
        connection.close.assert_called_once_with()
        self.assertTrue(close_observation.get("isolated"))
        self.assertEqual(report["blocker"], "ValueError")
        self.assertFalse(report["postgres_readonly_connection_qualified"])
        self.assertFalse(report["one_first_party_apply_qualified"])
        self.assertFalse(report["release_qualified"])

    def test_existing_process_alarm_refused_and_restored_before_imports(self):
        # A caller's existing SIGALRM belongs to that caller. PG qualification
        # cannot overwrite it or continue to Django/DB operations.
        original_path = list(sys.path)
        original_env = dict(os.environ)
        original_socket_connect = socket.socket.connect
        with (
            patch("tools.flind.qualify_isolated_postgres_wave173.safe_locations",
                  return_value=True),
            patch("tools.flind.qualify_isolated_postgres_wave173.signal.alarm", create=True,
                  side_effect=[47, 0]) as alarm,
            patch("tools.flind.qualify_isolated_postgres_wave173.subprocess.run",
                  side_effect=AssertionError("git_or_import_started")) as run,
        ):
            report = execute(
                self.repo, "HEAD", self.data, self.sock, 65443,
                "flind_wave173_synthetic", apply_rollback=True,
            )
        self.assertEqual([call.args[0] for call in alarm.call_args_list], [150, 47])
        run.assert_not_called()
        self.assertEqual(report["blocker"], "ValueError")
        self.assertFalse(report["postgres_readonly_connection_qualified"])
        self.assertFalse(report["one_first_party_apply_qualified"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual(sys.path, original_path)
        self.assertEqual(dict(os.environ), original_env)
        self.assertIs(socket.socket.connect, original_socket_connect)

    def test_unsafe_pg_location_never_changes_existing_process_alarm(self):
        with (
            patch("tools.flind.qualify_isolated_postgres_wave173.safe_locations",
                  return_value=False),
            patch("tools.flind.qualify_isolated_postgres_wave173.signal.alarm", create=True) as alarm,
        ):
            report = execute(
                self.repo, "HEAD", self.data, self.sock, 65443,
                "flind_wave173_synthetic", apply_rollback=True,
            )
        alarm.assert_not_called()
        self.assertEqual(report["blocker"], "ValueError")
        self.assertFalse(report["release_qualified"])

    def test_marked_private_scratch_paths_admit_only_distinct_directories(self):
        # Exercise the actual safe_locations() contract, not only its helper.
        private_tmp = Path("/private/tmp")
        if not private_tmp.is_dir():
            self.skipTest("macOS /private/tmp scratch is not available")
        with tempfile.TemporaryDirectory(prefix="flind-wave223-private-", dir=private_tmp) as tmp:
            base = Path(tmp)
            source, pg_data, pg_socket = (base / "source", base / "pg", base / "socket")
            for directory in (source, pg_data, pg_socket):
                directory.mkdir()
            (source / ".git").mkdir()
            (source / ".git" / "objects").mkdir()
            (source / "pyproject.toml").write_text("name='flind'")
            (source / SOURCE_MARKER).write_text(SOURCE_MARKER_TEXT)
            (pg_data / "PG_VERSION").write_text("17\n")
            (pg_data / PG_MARKER).write_text(PG_MARKER_TEXT)
            (pg_socket / ".s.PGSQL.65443").write_text("synthetic fixture only")
            self.assertTrue(safe_locations(
                source, pg_data, pg_socket, 65443, "flind_wave223_synthetic"
            ))
            (pg_data / "PG_VERSION").write_text("18\n")
            self.assertFalse(safe_locations(
                source, pg_data, pg_socket, 65443, "flind_wave223_synthetic"
            ))
            (pg_data / "PG_VERSION").write_text("17\n")
            nested = source / "socket"
            nested.mkdir()
            (nested / ".s.PGSQL.65443").write_text("synthetic fixture only")
            self.assertFalse(safe_locations(
                source, pg_data, nested, 65443, "flind_wave223_synthetic"
            ))
            nested_pg_socket = pg_data / "socket"
            nested_pg_socket.mkdir()
            (nested_pg_socket / ".s.PGSQL.65443").write_text("synthetic fixture only")
            self.assertFalse(safe_locations(
                source, pg_data, nested_pg_socket, 65443, "flind_wave223_synthetic"
            ))

    def test_only_one_exact_postgres_unix_socket_directory_accepted(self):
        expected = Path("/private/tmp/flind-wave223-private-socket")
        self.assertTrue(server_uses_only_approved_socket_dir(str(expected), expected))
        for directories in (
            "", "/tmp", "localhost", ".", str(expected) + ",/tmp",
            str(expected) + ", " + str(expected), str(expected) + "/",
            str(expected).replace("flind-wave223-private-socket", "flind-wave223-alias-socket"), None,
        ):
            with self.subTest(directories=directories):
                self.assertFalse(server_uses_only_approved_socket_dir(directories, expected))

    def test_source_data_and_socket_paths_cannot_overlap(self):
        source = Path("/private/tmp/flind-wave223-source")
        pg_data = Path("/private/tmp/flind-wave223-data")
        socket = Path("/private/tmp/flind-wave223-socket")
        self.assertTrue(paths_are_pairwise_disjoint(source, pg_data, socket))
        for overlapping in (
            (source, pg_data, source / "socket"),
            (source, pg_data, pg_data / "socket"),
            (source, socket, socket),
            (socket, pg_data, socket / "source"),
            (source, source, socket),
        ):
            with self.subTest(overlapping=overlapping):
                self.assertFalse(paths_are_pairwise_disjoint(*overlapping))

    def test_migration_plan_requires_real_pending_work(self):
        # A valid migration graph does not prove that any migrations are
        # pending; an empty plan must not be reported as qualified.
        leaf = [("ai_training", "0001_initial")]
        plan = [(SimpleNamespace(app_label=SMOKE_APP, name=SMOKE_MIGRATION), False)]
        self.assertTrue(has_pending_migration_plan(True, leaf, plan))
        self.assertFalse(has_pending_migration_plan(True, leaf, []))
        self.assertFalse(has_pending_migration_plan(True, [], plan))
        self.assertFalse(has_pending_migration_plan(False, leaf, plan))
        self.assertFalse(has_pending_migration_plan(False, [], []))

    def test_cli_refuses_incomplete_qualification_even_without_blocker(self):
        # A missing plan/PG proof must never print PASS or exit zero merely
        # because execute() returned without a Python exception.
        from tools.flind.qualify_isolated_postgres_wave173 import main

        required = (
            "django_registry_qualified", "migration_graph_qualified",
            "postgres_readonly_connection_qualified", "postgres_tcp_disabled_qualified",
            "postgres_socket_directory_qualified", "postgres_version_qualified",
            "migration_plan_qualified",
        )
        argv = [
            "flind-pg", "--root", str(self.repo), "--pg-data", str(self.data),
            "--pg-socket", str(self.sock), "--pg-port", "65443",
            "--dbname", "flind_wave223_synthetic",
        ]
        for missing in required:
            with self.subTest(missing=missing):
                report = {key: True for key in required}
                report[missing] = False
                with (
                    patch.object(sys, "argv", argv),
                    patch("tools.flind.qualify_isolated_postgres_wave173.execute",
                          return_value=report),
                    patch("builtins.print") as output,
                ):
                    self.assertEqual(main(), 2)
                    self.assertEqual(output.call_args.args[-1], "BLOCKED")

    def test_cli_requires_both_apply_and_rollback_receipts_when_requested(self):
        from tools.flind.qualify_isolated_postgres_wave173 import main

        report = {
            "django_registry_qualified": True, "migration_graph_qualified": True,
            "postgres_readonly_connection_qualified": True,
            "postgres_tcp_disabled_qualified": True,
            "postgres_socket_directory_qualified": True,
            "postgres_version_qualified": True,
            "migration_plan_qualified": True,
            "smoke_migration_source_qualified": True,
            "one_first_party_apply_qualified": False,
            "one_first_party_rollback_qualified": False,
        }
        argv = [
            "flind-pg", "--root", str(self.repo), "--pg-data", str(self.data),
            "--pg-socket", str(self.sock), "--pg-port", "65443",
            "--dbname", "flind_wave223_synthetic",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch("tools.flind.qualify_isolated_postgres_wave173.execute",
                  return_value=report),
            patch("builtins.print") as output,
        ):
            self.assertEqual(main(), 0)
            self.assertEqual(output.call_args.args[-1], "PASS")
        with (
            patch.object(sys, "argv", argv + ["--apply-rollback"]),
            patch("tools.flind.qualify_isolated_postgres_wave173.execute",
                  return_value=report),
            patch("builtins.print") as output,
        ):
            self.assertEqual(main(), 2)
            self.assertEqual(output.call_args.args[-1], "BLOCKED")
        # A rollback-only receipt must not qualify an apply+rollback run.
        report["one_first_party_rollback_qualified"] = True
        with (
            patch.object(sys, "argv", argv + ["--apply-rollback"]),
            patch("tools.flind.qualify_isolated_postgres_wave173.execute",
                  return_value=report),
            patch("builtins.print") as output,
        ):
            self.assertEqual(main(), 2)
            self.assertEqual(output.call_args.args[-1], "BLOCKED")
        report["one_first_party_apply_qualified"] = True
        with (
            patch.object(sys, "argv", argv + ["--apply-rollback"]),
            patch("tools.flind.qualify_isolated_postgres_wave173.execute",
                  return_value=report),
            patch("builtins.print") as output,
        ):
            self.assertEqual(main(), 0)
            self.assertEqual(output.call_args.args[-1], "PASS")

    def test_smoke_migration_pinned_blob_requires_exact_disk_and_git_bytes(self):
        # The original Django loader can import a staged migration directly,
        # bypassing the Git fallback loader. Compare both copies before writes.
        fixture = b"original first-party synthetic fixture\n"
        header = b"blob " + str(len(fixture)).encode("ascii") + b"\0"
        expected_blob = hashlib.sha1(header + fixture).hexdigest()
        path = self.repo / SMOKE_MIGRATION_PATH
        path.parent.mkdir(parents=True)
        path.write_bytes(fixture)

        class Reader:
            def __init__(self, content):
                self.content = content
            def read(self, path_name):
                if path_name != SMOKE_MIGRATION_PATH:
                    raise ValueError("unexpected_migration_path")
                return self.content

        self.assertEqual(SMOKE_MIGRATION_GIT_BLOB,
                         "e74ad4a9036c4118bddb3aff89f9a923b4b964ba")
        with patch("tools.flind.qualify_isolated_postgres_wave173.SMOKE_MIGRATION_GIT_BLOB",
                   expected_blob):
            self.assertTrue(smoke_migration_source_matches_commit(
                self.repo, Reader(fixture),
            ))
            self.assertFalse(smoke_migration_source_matches_commit(
                self.repo, Reader(b"changed committed migration"),
            ))
            path.write_bytes(b"uncommitted migration edit")
            self.assertFalse(smoke_migration_source_matches_commit(
                self.repo, Reader(fixture),
            ))
            path.unlink()
            try:
                path.symlink_to(self.repo / "pyproject.toml")
            except OSError as exc:
                # Unprivileged Windows cannot create filesystem symlinks.
                # Exercise the explicit symlink refusal with a mocked path.
                if not (os.name == "nt" and getattr(exc, "winerror", None) == 1314):
                    raise
                with patch.object(Path, "is_symlink", return_value=True):
                    self.assertFalse(smoke_migration_source_matches_commit(
                        self.repo, Reader(fixture),
                    ))
            else:
                self.assertFalse(smoke_migration_source_matches_commit(
                    self.repo, Reader(fixture),
                ))

    def test_smoke_migration_blob_pin_denies_mismatched_git_identity(self):
        fixture = b"original first-party synthetic fixture\n"
        path = self.repo / SMOKE_MIGRATION_PATH
        path.parent.mkdir(parents=True)
        path.write_bytes(fixture)

        class Reader:
            def read(self, path_name):
                if path_name != SMOKE_MIGRATION_PATH:
                    raise ValueError("unexpected_migration_path")
                return fixture

        # Even identical staged and Git bytes must fail without the
        # approved real first-party Git blob identity.
        self.assertFalse(smoke_migration_source_matches_commit(
            self.repo, Reader(),
        ))

    def test_first_party_migration_selector_does_not_accept_unscoped_ops(self):
        mig = SimpleNamespace(
            dependencies=[], operations=[CreateModel()],
        )
        plan = [(SimpleNamespace(app_label=SMOKE_APP, name=SMOKE_MIGRATION), False)]
        self.assertTrue(expected_migration(mig, plan))
        self.assertFalse(expected_migration(
            SimpleNamespace(dependencies=["other"], operations=[CreateModel()]), plan
        ))
        self.assertFalse(expected_migration(mig, [(plan[0][0], True)]))
        self.assertFalse(expected_migration(
            SimpleNamespace(dependencies=[], operations=[CreateModel([
                ("user", SimpleNamespace(remote_field="unsafe_relation"))
            ])]), plan
        ))
        self.assertFalse(expected_migration(mig, []))

    def test_project_source_and_pg_datadir_cannot_overlap(self):
        nested = self.repo / "postgres-cluster"
        nested.mkdir()
        (nested / "PG_VERSION").write_text("17")
        (nested / PG_MARKER).write_text(PG_MARKER_TEXT)
        self.assertFalse(safe_locations(
            self.repo, nested, self.sock, 65443, "flind_wave173_synthetic"
        ))


if __name__ == "__main__":
    unittest.main()
