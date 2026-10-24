"""Dependency-free concurrency tests executing Flind's real Django view methods.

Django/Redis/Postgres service E2E is a separate release gate. Rather than
asserting only source strings, extract the actual authorize/poll method AST
and execute it under minimal fake framework dependencies and an atomic cache.
"""
import ast
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier, Lock
import time
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "posthog/api/cli_auth.py"


class AtomicFakeCache:
    def __init__(self, *, get_barrier=None, barrier_key=None):
        self.data = {}
        self.lock = Lock()
        self.get_barrier = get_barrier
        self.barrier_key = barrier_key

    def get(self, key):
        if self.get_barrier is not None and key == self.barrier_key:
            self.get_barrier.wait(timeout=10)
        with self.lock:
            return copy.deepcopy(self.data.get(key))

    def set(self, key, value, timeout=None):
        with self.lock:
            self.data[key] = copy.deepcopy(value)

    def add(self, key, value, timeout=None):
        with self.lock:
            if key in self.data:
                return False
            self.data[key] = copy.deepcopy(value)
            return True

    def delete(self, key):
        with self.lock:
            self.data.pop(key, None)


class IdentitySerializer:
    def __init__(self, data):
        self.validated_data = data
        self.data = data

    def is_valid(self, raise_exception=False):
        return True


def actual_methods_scope(cache, mint):
    parsed = ast.parse(SOURCE.read_text())
    view = next(
        node for node in parsed.body
        if isinstance(node, ast.ClassDef) and node.name == "CLIAuthViewSet"
    )
    methods = []
    for name in ("device_code", "authorize", "poll"):
        method = copy.deepcopy(next(
            m for m in view.body
            if isinstance(m, ast.FunctionDef) and m.name == name
        ))
        method.decorator_list = []
        methods.append(method)
    for name in (
        "get_device_cache_key",
        "get_user_code_cache_key",
        "get_device_authorization_claim_key",
        "get_device_poll_claim_key",
    ):
        fn = copy.deepcopy(next(
            node for node in parsed.body
            if isinstance(node, ast.FunctionDef) and node.name == name
        ))
        methods.append(fn)

    team = SimpleNamespace(id=3, name="Flind local")
    team_model = SimpleNamespace(
        objects=SimpleNamespace(get=lambda **kw: team),
        DoesNotExist=type("DoesNotExist", (Exception,), {}),
    )
    fake_status = SimpleNamespace(
        HTTP_400_BAD_REQUEST=400,
        HTTP_403_FORBIDDEN=403,
        HTTP_200_OK=200,
        HTTP_202_ACCEPTED=202,
        HTTP_503_SERVICE_UNAVAILABLE=503,
    )
    scope = {
        "cache": cache,
        "Response": lambda data, status: SimpleNamespace(data=data, status_code=status),
        "status": fake_status,
        "DeviceCodeResponseSerializer": IdentitySerializer,
        "DeviceAuthorizationSerializer": IdentitySerializer,
        "DevicePollSerializer": IdentitySerializer,
        "DevicePollResponseSerializer": IdentitySerializer,
        "User": object,
        "Team": team_model,
        "AccessibleTeams": SimpleNamespace(for_request=lambda req, team_ids: team_ids),
        "CredentialScopeDenied": type("CredentialScopeDenied", (Exception,), {}),
        "PersonalAPIKey": SimpleNamespace(objects=SimpleNamespace(
            filter=lambda **kw: SimpleNamespace(exists=lambda: False),
        )),
        "mint_personal_api_key": mint,
        "validate_personal_api_key_scopes": lambda *args, **kwargs: None,
        "UNPRIVILEGED_SCOPES": ["error_tracking:write"],
        "CLI_SCOPES": ["error_tracking:write"],
        "DEVICE_CODE_EXPIRY_SECONDS": 600,
        "CLI_POLL_INTERVAL_SECONDS": 5,
        "generate_device_code": lambda: "device-allocated-by-test",
        "generate_user_code": lambda: "WXYZ-9876",
        "timezone": SimpleNamespace(now=lambda: datetime.now(timezone.utc)),
        "serializers": SimpleNamespace(ValidationError=type("ValidationError", (Exception,), {})),
        "get_validation_error_description": lambda exc: str(exc),
    }
    module = ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[]))
    exec(compile(module, str(SOURCE), "exec"), scope)
    return scope


class TestCliDeviceClaimConcurrency(unittest.TestCase):
    def test_16_concurrent_authorizations_mint_only_one_token(self):
        cache = AtomicFakeCache()
        minted = []
        minted_lock = Lock()

        def mint(*args, **kwargs):
            with minted_lock:
                minted.append(kwargs["label"])
            time.sleep(0.035)
            return SimpleNamespace(value="phx_test_only", key=SimpleNamespace(mask_value="phx_****"))

        scope = actual_methods_scope(cache, mint)
        code, user_code = "test-device-token", "ABCD-1234"
        cache.set(scope["get_device_cache_key"](code), {
            "user_code": user_code,
            "status": "pending",
        })
        cache.set(scope["get_user_code_cache_key"](user_code), code)
        user = SimpleNamespace(id=19, credentials_reviewed_at=datetime.now(timezone.utc))
        request = SimpleNamespace(user=user, data={
            "user_code": user_code,
            "project_id": 3,
            "scopes": ["error_tracking:write"],
        })
        start = Barrier(16)

        def run():
            start.wait(timeout=10)
            return scope["authorize"](None, request)

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(lambda _: run(), range(16)))
        self.assertEqual(len(minted), 1)
        self.assertEqual(sum(r.status_code == 200 for r in results), 1)
        self.assertEqual(sum(r.status_code == 400 for r in results), 15)
        self.assertTrue(all(
            r.data.get("error") in ("already_authorizing", "already_authorized")
            for r in results if r.status_code == 400
        ))

    def test_concurrent_polls_deliver_authorized_token_exactly_once(self):
        code = "test-poll-token"
        readers = Barrier(16)
        cache = AtomicFakeCache(
            get_barrier=readers, barrier_key="cli_device:" + code,
        )
        scope = actual_methods_scope(cache, lambda *a, **k: None)
        cache.set(scope["get_device_cache_key"](code), {
            "user_code": "ABCD-1234",
            "status": "authorized",
            "personal_api_key": "phx_test_only",
            "label": "CLI test",
            "project_id": "3",
            "scopes": ["error_tracking:write"],
        })
        cache.set(scope["get_user_code_cache_key"]("ABCD-1234"), code)
        request = SimpleNamespace(data={"device_code": code})

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(
                lambda _: scope["poll"](None, request), range(16),
            ))
        self.assertEqual(sum(r.status_code == 200 for r in results), 1)
        self.assertEqual(sum(r.status_code == 400 for r in results), 15)
        self.assertEqual(sum("personal_api_key" in r.data for r in results), 1)

    def test_user_code_collision_never_overwrites_first_device(self):
        cache = AtomicFakeCache()
        scope = actual_methods_scope(cache, lambda *args, **kwargs: None)
        key = scope["get_user_code_cache_key"]("ABCD-1234")
        cache.set(key, "first-device")
        codes = iter(("ABCD-1234", "WXYZ-9876"))
        scope["generate_user_code"] = lambda: next(codes)
        request = SimpleNamespace(build_absolute_uri=lambda path: "http://localhost:8010/")

        result = scope["device_code"](None, request)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["user_code"], "WXYZ-9876")
        self.assertEqual(cache.get(key), "first-device")
        self.assertEqual(
            cache.get(scope["get_user_code_cache_key"]("WXYZ-9876")),
            "device-allocated-by-test",
        )

    def test_user_code_exhaustion_returns_503_without_reassigning_code(self):
        cache = AtomicFakeCache()
        scope = actual_methods_scope(cache, lambda *args, **kwargs: None)
        key = scope["get_user_code_cache_key"]("ABCD-1234")
        cache.set(key, "first-device")
        scope["generate_user_code"] = lambda: "ABCD-1234"
        request = SimpleNamespace(build_absolute_uri=lambda path: "http://localhost:8010/")

        result = scope["device_code"](None, request)

        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.data["error"], "temporarily_unavailable")
        self.assertEqual(cache.get(key), "first-device")

    def test_failed_mint_releases_claim_without_returning_token(self):
        cache = AtomicFakeCache()
        def failed_mint(*args, **kwargs):
            raise ValueError("synthetic mint failure")
        scope = actual_methods_scope(cache, failed_mint)
        code, user_code = "test-failure", "ABCD-5678"
        cache.set(scope["get_device_cache_key"](code), {
            "user_code": user_code, "status": "pending",
        })
        cache.set(scope["get_user_code_cache_key"](user_code), code)
        request = SimpleNamespace(
            user=SimpleNamespace(id=19, credentials_reviewed_at=datetime.now(timezone.utc)),
            data={"user_code": user_code, "project_id": 3},
        )
        with self.assertRaisesRegex(ValueError, "synthetic mint failure"):
            scope["authorize"](None, request)
        self.assertIsNone(cache.get(scope["get_device_authorization_claim_key"](code)))


if __name__ == "__main__":
    unittest.main()
