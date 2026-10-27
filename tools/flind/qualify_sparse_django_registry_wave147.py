#!/usr/bin/env python3
"""Read-only Django app-registry probe for Git sparse/partial Flind checkouts.

Load missing tracked first-party Python imports directly from Git blobs, without
expanding giant subtrees or writing source files into the checkout. The probe
explicitly denies Python network sockets and uses fake loopback service URLs.
This qualifies at most the app registry, NEVER migrations or the release.
"""
from __future__ import annotations

import argparse
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ALLOWED_ROOTS = ("posthog", "products", "ee", "common", "flind")
MAX_INDEX_BYTES = 16 * 1024 * 1024
MAX_BLOB_BYTES = 2 * 1024 * 1024
MAX_IMPORTS = 3000
MAX_SECONDS = 180
_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){0,24}$")
RECEIPT_PREFIX = "FLIND_REGISTRY_PROBE_RECEIPT="


def git_offline_env() -> dict[str, str]:
    """Never allow Git's promisor/partial clone to fetch missing source implicitly."""
    return {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}



def index_tracked_python(root: Path, ref: str) -> set[str]:
    """Enumerate tracked source names once; no repo expansion or checkout writes."""
    if not re.fullmatch(r"[a-zA-Z0-9_./-]{1,128}", ref) or ref.startswith("-"):
        raise ValueError("Unsafe Git source reference")
    result = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", ref,
         "--", *ALLOWED_ROOTS],
        capture_output=True, timeout=45, check=False, env=git_offline_env(),
    )
    if result.returncode or len(result.stdout) > MAX_INDEX_BYTES:
        raise RuntimeError("Could not safely index first-party Python sources")
    return {
        path.decode("utf-8")
        for path in result.stdout.splitlines()
        if path.endswith(b".py") and b".." not in path
    }


class GitBlobBatchReader:
    """One offline Git process for all source imports; no lazy remote blob fetch."""

    def __init__(self, root: Path, ref: str):
        self.ref = ref
        self.process = subprocess.Popen(
            ["git", "-C", str(root), "cat-file", "--batch"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=git_offline_env(),
        )

    def read(self, path: str) -> bytes:
        if ("\n" in path or "\r" in path or path.startswith("/")
                or ".." in Path(path).parts or not path.endswith(".py")):
            raise ValueError("Unsafe tracked source path")
        proc = self.process
        if proc.poll() is not None or proc.stdin is None or proc.stdout is None:
            raise ImportError("Offline Git batch reader unavailable")
        try:
            proc.stdin.write((self.ref + ":" + path + "\n").encode("utf-8"))
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ImportError("Tracked blob unavailable offline")
            size = int(header[2])
            if size < 0 or size > MAX_BLOB_BYTES:
                raise ImportError("Tracked blob exceeds source budget")
            data = proc.stdout.read(size)
            if len(data) != size or proc.stdout.read(1) != b"\n":
                raise ImportError("Malformed offline Git batch response")
            return data
        except (OSError, ValueError) as exc:
            raise ImportError("Offline Git batch source read failed") from exc

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
        finally:
            # A terminated child still leaves Python's pipe descriptors open.
            # Close both ends so repeated probes do not leak file handles.
            for pipe in (self.process.stdin, self.process.stdout):
                if pipe is not None:
                    pipe.close()


class GitTrackedPythonLoader(importlib.abc.Loader):
    def __init__(self, finder: "GitTrackedPythonFinder", path: str, package: bool) -> None:
        self.finder = finder
        self.path = path
        self.package = package

    def create_module(self, spec):
        return None

    def exec_module(self, module) -> None:
        finder = self.finder
        if finder.loaded >= finder.limit:
            raise ImportError("Flind tracked-source module admission limit reached")
        if time.monotonic() - finder.started > finder.deadline:
            raise ImportError("Flind tracked-source import deadline exceeded")
        if finder.batch_reader is not None:
            try:
                source_bytes = finder.batch_reader.read(self.path)
            except (ImportError, OSError, ValueError) as exc:
                finder.last_unavailable_source = self.path
                finder.source_failure_kind = "offline_batch_blob_read_failed"
                raise ImportError("Flind offline tracked source unavailable") from exc
        else:
            # Preserve the fixture-facing legacy code path for existing unit tests.
            try:
                result = subprocess.run(
                    ["git", "-C", str(finder.root), "show", finder.ref + ":" + self.path],
                    capture_output=True, timeout=18, check=False, env=git_offline_env(),
                )
            except subprocess.TimeoutExpired as exc:
                finder.last_unavailable_source = self.path
                finder.source_failure_kind = "bounded_local_git_timeout"
                raise ImportError("Flind tracked source read exceeded time budget") from exc
            if result.returncode or len(result.stdout) > MAX_BLOB_BYTES:
                finder.last_unavailable_source = self.path
                finder.source_failure_kind = (
                    "missing_local_git_blob" if result.returncode else "source_blob_over_size_budget"
                )
                raise ImportError("Flind tracked source unavailable locally or over size budget")
            source_bytes = result.stdout
        try:
            contents = source_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            finder.last_unavailable_source = self.path
            finder.source_failure_kind = "non_utf8_source"
            raise ImportError("Non-UTF8 first-party Python source") from exc
        module.__file__ = str(finder.root / self.path)
        if self.package:
            module.__path__ = [str((finder.root / self.path).parent)]
        finder.loaded += 1
        finder.last_traced_source = self.path
        exec(compile(contents, module.__file__, "exec"), module.__dict__)


class GitTrackedPythonFinder(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path, ref: str, paths: set[str],
                 *, limit: int = MAX_IMPORTS, deadline: int = MAX_SECONDS,
                 batch_reader: GitBlobBatchReader | None = None) -> None:
        if not 0 < limit <= MAX_IMPORTS or not 0 < deadline <= MAX_SECONDS:
            raise ValueError("Invalid bounded import limits")
        self.root = root.resolve()
        self.ref = ref
        self.paths = paths
        # Tracked namespace packages may not have __init__.py *or an on-disk
        # directory* in sparse checkouts. Restore PEP 420 package discovery
        # only for paths backed by tracked first-party Python descendants.
        prefixes: set[str] = set()
        for source in paths:
            segments = source.split("/")
            for depth in range(1, len(segments)):
                prefix = "/".join(segments[:depth])
                if prefix + "/__init__.py" not in paths:
                    prefixes.add(prefix)
        self.namespace_prefixes = prefixes
        self.batch_reader = batch_reader
        self.limit = limit
        self.deadline = deadline
        self.started = time.monotonic()
        self.loaded = 0
        self.last_traced_source: str | None = None
        self.last_unavailable_source: str | None = None
        self.source_failure_kind: str | None = None

    def find_spec(self, fullname: str, path=None, target=None):
        if not _SAFE_NAME.fullmatch(fullname):
            return None
        parts = fullname.split(".")
        if parts[0] not in ALLOWED_ROOTS:
            return None
        rel = "/".join(parts)
        for candidate, package in ((rel + "/__init__.py", True),
                                   (rel + ".py", False)):
            if candidate not in self.paths:
                continue
            loader = GitTrackedPythonLoader(self, candidate, package)
            return importlib.util.spec_from_loader(fullname, loader, is_package=package)
        if rel in self.namespace_prefixes:
            spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = [str(self.root / rel)]
            return spec
        return None


def local_missing_resource(root: Path, error: FileNotFoundError) -> str | None:
    """Report only bounded, repository-relative missing resource paths."""
    if not isinstance(error.filename, str):
        return None
    try:
        relative = Path(error.filename).resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    name = relative.as_posix()
    if not name or len(name) > 300 or ".." in relative.parts:
        return None
    return name


def registry_child(root: Path, ref: str, limit: int, deadline: int) -> int:
    import socket

    def refuse_socket(*args, **kwargs):
        raise OSError("Flind isolated registry probe denies socket access")

    socket.socket.connect = refuse_socket
    socket.socket.connect_ex = refuse_socket
    socket.create_connection = refuse_socket

    receipt = {
        "django_registry_qualified": False,
        "traced_source_modules": 0,
        "release_qualified": False,
        "migrations_qualified": False,
        "app_http_qualified": False,
        "blocker": "Unknown Django registry failure",
    }
    finder = None
    batch_reader = None
    try:
        tracked = index_tracked_python(root, ref)
        batch_reader = GitBlobBatchReader(root, ref)
        finder = GitTrackedPythonFinder(root, ref, tracked, limit=limit,
                                        deadline=deadline, batch_reader=batch_reader)
        # Existing files and installed third-party wheels are preferred.
        sys.meta_path.append(finder)
        import django
        django.setup()
        from django.apps import apps
        receipt["django_registry_qualified"] = True
        receipt["app_count"] = len(apps.get_app_configs())
        receipt.pop("blocker")
    except ModuleNotFoundError as e:
        receipt["blocker"] = "Missing tracked or third-party module"
        if isinstance(e.name, str) and _SAFE_NAME.fullmatch(e.name):
            receipt["missing_module"] = e.name
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        receipt["blocker"] = type(e).__name__
        if isinstance(e, FileNotFoundError):
            missing = local_missing_resource(root, e)
            if missing is not None:
                receipt["missing_local_resource"] = missing
        if isinstance(e, ImportError):
            if isinstance(e.name, str) and _SAFE_NAME.fullmatch(e.name):
                receipt["import_error_name"] = e.name
            if str(e) == "Flind tracked-source import deadline exceeded":
                receipt["source_failure_kind"] = "source_import_deadline"
            elif str(e) == "Flind tracked-source module admission limit reached":
                receipt["source_failure_kind"] = "source_import_limit"
    except Exception:
        receipt["blocker"] = "Unhandled first-party registry error"
    finally:
        if batch_reader is not None:
            batch_reader.close()
        receipt["traced_source_modules"] = finder.loaded if finder else 0
        if finder is not None and not receipt["django_registry_qualified"] and finder.last_traced_source is not None:
            # Diagnostic context, not proof that this was the failed import.
            receipt["last_traced_source"] = finder.last_traced_source
        if finder is not None and finder.last_unavailable_source is not None:
            # Relative Git-tracked source path only; never leak machine/user paths.
            receipt["blocked_tracked_source"] = finder.last_unavailable_source
            receipt["source_failure_kind"] = finder.source_failure_kind
        print(RECEIPT_PREFIX + json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt["django_registry_qualified"] else 2


def probe(root: Path, ref: str, *, deadline: int = 150, limit: int = 2200) -> dict:
    """Run Django in a separate bounded process with only synthetic credentials."""
    root = root.resolve()
    result = {
        "phase": "sparse-git-django-app-registry",
        "source_ref": ref,
        "django_registry_qualified": False,
        "migrations_qualified": False,
        "app_http_qualified": False,
        "real_ingest_qualified": False,
        "tenant_isolation_qualified": False,
        "release_qualified": False,
    }
    if not 0 < deadline <= MAX_SECONDS or not 0 < limit <= MAX_IMPORTS:
        return {**result, "blocker": "Invalid bounded limits"}
    if not (root / "pyproject.toml").is_file():
        return {**result, "blocker": "Flind repository root missing"}
    # Pin evidence to the actual local commit rather than a moving branch ref.
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", ref + "^{commit}"],
            capture_output=True, check=False, timeout=20, env=git_offline_env(),
        )
        resolved = commit.stdout.decode("ascii").strip()
        if (commit.returncode or len(resolved) not in (40, 64)
                or not re.fullmatch("[0-9a-f]+", resolved)):
            return {**result, "blocker": "Git source commit could not be verified"}
        result["source_commit"] = resolved
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return {**result, "blocker": "Git source commit could not be verified"}
    env = {
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C",
        "DJANGO_SETTINGS_MODULE": "posthog.settings",
        "SECRET_KEY": "flind_test_only_ephemeral_not_for_deploy",
        "DATABASE_URL": "postgresql://no_user:no_password@127.0.0.1:65433/flind_nonexistent",
        "POSTHOG_DB_NAME": "flind_nonexistent",
        "REDIS_URL": "redis://127.0.0.1:65434/0",
        "CLICKHOUSE_HOST": "127.0.0.1",
        "CLICKHOUSE_PORT": "65435",
        "KAFKA_HOSTS": "127.0.0.1:65437",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(root),
    }
    argv = [sys.executable, str(Path(__file__).resolve()), "--child",
            "--root", str(root), "--ref", ref,
            "--max-imports", str(limit), "--timeout", str(deadline)]
    with tempfile.TemporaryFile(mode="w+t") as output:
        process = subprocess.Popen(
            argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
        )
        timed_out = False
        try:
            process.wait(timeout=deadline + 15)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        output.seek(0)
        data = None
        for line in output:
            if line.startswith(RECEIPT_PREFIX):
                try:
                    candidate = json.loads(line[len(RECEIPT_PREFIX):])
                    if isinstance(candidate, dict):
                        data = candidate
                except json.JSONDecodeError:
                    pass
    if timed_out:
        result["blocker"] = "Bounded Django registry probe timed out"
    elif data is None:
        result["blocker"] = "Django registry process returned no valid receipt"
    else:
        for key in ("django_registry_qualified", "traced_source_modules",
                    "app_count", "blocker", "missing_module",
                    "blocked_tracked_source", "source_failure_kind",
                    "last_traced_source", "import_error_name",
                    "missing_local_resource"):
            if key in data:
                result[key] = data[key]
        if process.returncode != 0:
            result["django_registry_qualified"] = False
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    p.add_argument("--ref", default="HEAD")
    p.add_argument("--timeout", type=int, default=150)
    p.add_argument("--max-imports", type=int, default=2200)
    p.add_argument("--child", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    if args.child:
        return registry_child(Path(args.root), args.ref, args.max_imports, args.timeout)
    report = probe(Path(args.root), args.ref, deadline=args.timeout, limit=args.max_imports)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Flind sparse Django registry:", "PASS" if report["django_registry_qualified"] else "BLOCKED")
        print("Full migrations, API, workers, tenant isolation and release: NOT QUALIFIED")
    return 0 if report["django_registry_qualified"] else 2


if __name__ == "__main__":
    sys.exit(main())
