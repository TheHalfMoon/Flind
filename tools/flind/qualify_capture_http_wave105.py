#!/usr/bin/env python3
"""Qualify Flind's real Django internal Capture-v1 HTTP client against loopback.

Real HTTP requests, real requests.Session and Flind's production capture_batch_internal.
The receiver is an intentionally small synthetic protocol fixture, NOT capture-rs,
Kafka, production ingestion or a product authenticated dashboard.
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


FIXED_IDS = tuple(str(UUID(int=i)) for i in (1001, 1002, 1003))
ENDPOINT = "/i/v1/analytics/events"


def closed(reason: str) -> dict:
    return {
        "real_internal_capture_http_client_qualified": False,
        "first_party_sdk_headers_on_http": False,
        "correct_batch_sent": False,
        "only_retry_unacked_event": False,
        "retry_incremented_attempt": False,
        "accepted_event_not_duplicated": False,
        "invalid_json_fails_closed": False,
        "replay_event_rejected_before_http": False,
        "capture_http_loopback_receipts_verified": False,
        "temporary_loopback_fixture_only": True,
        "capture_rust_server_qualified": False,
        "production_kafka_event_ingestion_qualified": False,
        "clickhouse_product_events_qualified": False,
        "tenant_authorization_qualified": False,
        "dashboard_browser_e2e_qualified": False,
        "release_qualified": False,
        "blocker": reason,
    }


class CaptureStub(BaseHTTPRequestHandler):
    server_version = "FlindSyntheticCaptureTest/1"
    sys_version = ""

    def do_POST(self):
        service = self.server
        if self.path != ENDPOINT or len(service.requests) >= 3:
            self.send_error(404)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if not 0 < content_length <= 16000:
                raise ValueError("invalid envelope length")
            body = json.loads(self.rfile.read(content_length))
            entries = body["batch"]
            ids = [entry["uuid"] for entry in entries]
            if not isinstance(entries, list) or not 1 <= len(entries) <= 2:
                raise ValueError("invalid batch shape")
            if any(type(entry) is not dict for entry in entries):
                raise ValueError("invalid event data")
            index = len(service.requests)
            observed = {
                "path_ok": self.path == ENDPOINT,
                "sdk_header_ok": self.headers.get("User-Agent") == "flind-capture-v1-internal/1.0"
                                 and self.headers.get("PostHog-Sdk-Info") == "flind-capture-v1-internal/1.0",
                "auth_header_ok": self.headers.get("Authorization", "").startswith("Bearer synthetic_"),
                "content_type_ok": self.headers.get("Content-Type", "").split(";")[0] == "application/json",
                "attempt": self.headers.get("PostHog-Attempt"),
                "ids": ids,
                "created_at_present": isinstance(body.get("created_at"), str),
                "internal_flag": body.get("capture_internal") is True,
                "historical_flag": body.get("historical_migration") is False,
                "events_have_required_fields": all(
                    isinstance(entry.get("event"), str)
                    and isinstance(entry.get("distinct_id"), str)
                    and isinstance(entry.get("timestamp"), str)
                    and isinstance(entry.get("properties"), dict)
                    for entry in entries
                ),
            }
            service.requests.append(observed)
            if index == 0:
                response = {"results": {
                    FIXED_IDS[0]: {"result": "ok"},
                    FIXED_IDS[1]: {"result": "retry"},
                }}
                raw = json.dumps(response, separators=(",", ":")).encode()
            elif index == 1:
                raw = json.dumps({"results": {
                    FIXED_IDS[1]: {"result": "ok"},
                }}).encode()
            else:
                raw = b"{invalid-fixture"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError):
            service.requests.append({"invalid_envelope": True})
            self.send_error(400)

    def log_message(self, format, *args):
        # Do not log authorization tokens, path or client addresses.
        return


def child_proof() -> dict:
    # This is a separate child with scrubbed environment and no personal tokens.
    import django
    django.setup()
    from posthog.api.capture import (
        CaptureInternalError, capture_batch_internal,
    )

    token = "synthetic_" + secrets.token_hex(18)
    events = [
        {"event": "$pageview", "distinct_id": "synthetic-a", "event_uuid": FIXED_IDS[0],
         "properties": {"page": "/flind-home"}},
        {"event": "purchase", "distinct_id": "synthetic-b", "event_uuid": FIXED_IDS[1],
         "properties": {"amount": 1}},
    ]
    accepted = capture_batch_internal(events=events, token=token,
                                      event_source="flind_wave105_local",
                                      max_attempts=2, timeout=3)
    failed = capture_batch_internal(
        events=[{"event": "$pageview", "distinct_id": "synthetic-c",
                 "event_uuid": FIXED_IDS[2], "properties": {"page": "/malformed"}}],
        token=token, event_source="flind_wave105_bad_reply",
        max_attempts=1, timeout=3,
    )
    blocked_replay = False
    try:
        capture_batch_internal(
            events=[{"event": "$snapshot", "distinct_id": "synthetic-c"}],
            token=token, event_source="flind_wave105_replay",
            max_attempts=1, timeout=3,
        )
    except CaptureInternalError:
        blocked_replay = True
    return {
        "two_event_retry_completed": accepted.succeeded() and sorted(accepted.ok) == sorted(FIXED_IDS[:2]),
        "bad_json_detected": not failed.succeeded() and FIXED_IDS[2] in failed.unaccounted
                             and failed.error is not None,
        "replay_rejected": blocked_replay,
    }


def qualify_capture_http() -> dict:
    if audit_runtime_lock().get("direct_lock_qualified") is not True:
        return closed("Frozen Django direct dependency lock incomplete")
    server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureStub)
    server.requests = []
    server.daemon_threads = True
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        env = isolated_boot_environment()
        env["PYTHONPATH"] = os.getcwd()
        env["CAPTURE_INTERNAL_URL"] = f"http://127.0.0.1:{server.server_address[1]}"
        env["CAPTURE_AI_INTERNAL_URL"] = "http://127.0.0.1:65439"
        env["HTTP_PROXY"] = "http://127.0.0.1:65440"
        env["HTTPS_PROXY"] = "http://127.0.0.1:65440"
        # The production internal_requests_session has trust_env=False; a
        # malicious proxy env must not capture internal bearer tokens.
        process = subprocess.run(
            [sys.executable, "-m", "tools.flind.qualify_capture_http_wave105", "--child"],
            env=env, cwd=os.getcwd(), capture_output=True, text=True,
            timeout=105, check=False,
        )
        if process.returncode or len(process.stdout) > 5000:
            return closed("Sanitized production Capture-v1 subprocess failed")
        try:
            child = json.loads(process.stdout)
        except (ValueError, TypeError):
            return closed("Synthetic capture child did not return a valid receipt")
        requests = list(server.requests)
        if len(requests) != 3:
            return closed("Actual HTTP fixture did not receive exactly three bounded requests")
        expected_batches = [[FIXED_IDS[0], FIXED_IDS[1]], [FIXED_IDS[1]], [FIXED_IDS[2]]]
        fields = [
            "path_ok", "sdk_header_ok", "auth_header_ok",
            "content_type_ok", "created_at_present", "internal_flag",
            "historical_flag", "events_have_required_fields",
        ]
        headers_ok = all(all(r.get(f) is True for f in fields) for r in requests)
        receipt = closed("Loopback Capture-v1 client scenario mismatch")
        receipt.update({
            "first_party_sdk_headers_on_http": headers_ok,
            "correct_batch_sent": requests[0].get("ids") == expected_batches[0],
            "only_retry_unacked_event": requests[1].get("ids") == expected_batches[1],
            "retry_incremented_attempt": [
                item.get("attempt") for item in requests
            ] == ["1", "2", "1"],
            "accepted_event_not_duplicated": all(
                r.get("ids", []).count(FIXED_IDS[0]) == (1 if i == 0 else 0)
                for i, r in enumerate(requests)
            ),
            "invalid_json_fails_closed": child.get("bad_json_detected") is True,
            "replay_event_rejected_before_http": child.get("replay_rejected") is True,
            "capture_http_loopback_receipts_verified": len(requests) == 3
                                               and child.get("two_event_retry_completed") is True,
        })
        # This receiver cannot assert global DNS/egress isolation; the last
        # predicate proves only this client's requests arrived on loopback.
        receipt["real_internal_capture_http_client_qualified"] = all(
            receipt[key] for key in (
                "first_party_sdk_headers_on_http", "correct_batch_sent",
                "only_retry_unacked_event", "retry_incremented_attempt",
                "accepted_event_not_duplicated", "invalid_json_fails_closed",
                "replay_event_rejected_before_http", "capture_http_loopback_receipts_verified",
            )
        )
        if receipt["real_internal_capture_http_client_qualified"]:
            receipt.pop("blocker")
        return receipt
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return closed("Loopback capture fixture process unavailable")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=4)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child:
        print(json.dumps(child_proof()))
        return 0
    result = qualify_capture_http()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flind real internal capture HTTP:", "PASS" if result["real_internal_capture_http_client_qualified"] else "BLOCKED")
        print("Native Rust capture, production Kafka and dashboard: NOT QUALIFIED")
    return 0 if result["real_internal_capture_http_client_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
