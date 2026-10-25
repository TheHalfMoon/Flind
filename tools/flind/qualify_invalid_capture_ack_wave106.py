#!/usr/bin/env python3
"""Live loopback HTTP checks for malformed capture acknowledgements.

Sends actual internal Capture-v1 Django client requests to disposable HTTP
receiver. Not a native Rust capture server, Kafka consumer or ClickHouse test.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import subprocess
import sys
from threading import Thread
from uuid import UUID

if __package__:
    from .qualify_django_lock import audit_runtime_lock
    from .qualify_django_boot_wave53 import isolated_boot_environment
else:
    from qualify_django_lock import audit_runtime_lock
    from qualify_django_boot_wave53 import isolated_boot_environment

CASES = {
    str(UUID(int=4001)): (200, {}),  # no status must not be "ok"
    str(UUID(int=4002)): (200, {"result": ["ok"]}),  # unhashable status
    str(UUID(int=4003)): (422, ["bad upstream response"]),  # non-object HTTP error
    str(UUID(int=4004)): (200, {"result": "ok"}),  # genuine ack still succeeds
}
ENDPOINT = "/i/v1/analytics/events"


def refused(reason: str) -> dict:
    return {
        "real_capture_invalid_ack_http_qualified": False,
        "missing_result_unaccounted": False,
        "unhashable_result_unaccounted": False,
        "nonobject_422_is_structured_failure": False,
        "valid_ack_still_success": False,
        "all_requests_reached_loopback": False,
        "first_party_capture_identity": False,
        "production_capture_rust_qualified": False,
        "production_kafka_ingestion_qualified": False,
        "product_clickhouse_schema_qualified": False,
        "product_query_api_qualified": False,
        "dashboard_e2e_qualified": False,
        "release_qualified": False,
        "blocker": reason,
    }


class FakeMalformedCaptureV1(BaseHTTPRequestHandler):
    server_version = "Flind-TestOnly/1"
    sys_version = ""

    def do_POST(self):
        srv = self.server
        if self.path != ENDPOINT or len(srv.receipts) >= len(CASES):
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size < 8000:
                raise ValueError("oversized")
            body = json.loads(self.rfile.read(size))
            ids = [event["uuid"] for event in body["batch"]]
            if len(ids) != 1 or ids[0] not in CASES:
                raise ValueError("unexpected id")
            uid = ids[0]
            status_code, val = CASES[uid]
            result = {"results": {uid: val}} if status_code == 200 else val
            raw = json.dumps(result, separators=(",", ":")).encode()
            srv.receipts.append({
                "uuid": uid,
                "sdk": self.headers.get("User-Agent") == "flind-capture-v1-internal/1.0"
                       and self.headers.get("PostHog-Sdk-Info") == "flind-capture-v1-internal/1.0",
                "capture_internal": body.get("capture_internal") is True,
                "auth_is_synthetic": self.headers.get("Authorization", "").startswith("Bearer synthetic_"),
            })
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (KeyError, TypeError, ValueError, AttributeError):
            self.send_error(400)

    def log_message(self, format, *args):
        return


def exercise_real_producer() -> dict:
    import django
    django.setup()
    from posthog.api.capture import CaptureInternalError, capture_batch_internal

    token = "synthetic_" + secrets.token_hex(16)
    outcomes: dict[str, bool] = {}
    for i, uid in enumerate(CASES):
        result = capture_batch_internal(
            events=[{
                "event": "$pageview", "distinct_id": "synthetic-wave106",
                "event_uuid": uid, "properties": {"$pathname": "/test"},
            }],
            token=token, event_source="flind_wave106_response_contract",
            max_attempts=1, timeout=3,
        )
        try:
            result.raise_for_status()
            raised = False
        except CaptureInternalError:
            raised = True
        if i == 0:
            outcomes["missing_result_unaccounted"] = bool(
                raised and not result.succeeded()
                and result.unaccounted == [uid]
                and result.results.get(uid) == {"result": "unaccounted"}
            )
        elif i == 1:
            outcomes["unhashable_result_unaccounted"] = bool(
                raised and not result.succeeded()
                and result.unaccounted == [uid]
                and result.results.get(uid) == {"result": "unaccounted"}
            )
        elif i == 2:
            outcomes["nonobject_422_is_structured_failure"] = bool(
                raised and not result.succeeded()
                and result.status_code == 422
                and result.unaccounted == [uid]
                and isinstance(result.error, dict)
                and result.error.get("error") == "invalid_response"
            )
        else:
            outcomes["valid_ack_still_success"] = bool(
                not raised and result.succeeded()
                and result.ok == [uid] and not result.unaccounted
            )
    return outcomes


def qualify_invalid_ack_http() -> dict:
    if audit_runtime_lock().get("direct_lock_qualified") is not True:
        return refused("Locked Django direct deps unavailable")
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeMalformedCaptureV1)
    server.daemon_threads = True
    server.receipts = []
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        env = isolated_boot_environment()
        env["PYTHONPATH"] = os.getcwd()
        env["CAPTURE_INTERNAL_URL"] = f"http://127.0.0.1:{server.server_port}"
        env["CAPTURE_AI_INTERNAL_URL"] = "http://127.0.0.1:65438"
        env["HTTP_PROXY"] = "http://127.0.0.1:65437"
        env["HTTPS_PROXY"] = "http://127.0.0.1:65437"
        process = subprocess.run(
            [sys.executable, "-m", "tools.flind.qualify_invalid_capture_ack_wave106", "--child"],
            cwd=os.getcwd(), env=env, capture_output=True, text=True,
            timeout=105, check=False,
        )
        if process.returncode != 0 or len(process.stdout) > 2000:
            return refused("Django Capture-v1 real HTTP child unavailable")
        try:
            outcomes = json.loads(process.stdout)
        except (TypeError, ValueError):
            return refused("Malformed child diagnostic")
        receipt = refused("Malformed Capture-v1 HTTP response rejected test criteria")
        receipt.update({k: outcomes.get(k) is True for k in (
            "missing_result_unaccounted", "unhashable_result_unaccounted",
            "nonobject_422_is_structured_failure", "valid_ack_still_success",
        )})
        observed = list(server.receipts)
        receipt["all_requests_reached_loopback"] = (
            len(observed) == len(CASES)
            and [r["uuid"] for r in observed] == list(CASES)
        )
        receipt["first_party_capture_identity"] = (
            len(observed) == len(CASES)
            and all(r["sdk"] and r["auth_is_synthetic"] and r["capture_internal"] for r in observed)
        )
        passed = all(receipt[k] for k in (
            "missing_result_unaccounted", "unhashable_result_unaccounted",
            "nonobject_422_is_structured_failure", "valid_ack_still_success",
            "all_requests_reached_loopback", "first_party_capture_identity",
        ))
        receipt["real_capture_invalid_ack_http_qualified"] = passed
        if passed:
            receipt.pop("blocker")
        return receipt
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return refused("Loopback Capture-v1 fixture process unavailable")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=4)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child:
        print(json.dumps(exercise_real_producer()))
        return 0
    report = qualify_invalid_ack_http()
    print(json.dumps(report, indent=2) if args.json
          else "Malformed v1 HTTP acknowledgements: " +
               ("PASS" if report["real_capture_invalid_ack_http_qualified"] else "BLOCKED"))
    return 0 if report["real_capture_invalid_ack_http_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
