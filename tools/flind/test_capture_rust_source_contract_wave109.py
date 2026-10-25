"""Cross-language first-party Python Capture-v1 ↔ actual Rust source contracts.

Source-backed regression guard only: DOES NOT compile or execute Rust,
persist to Kafka/ClickHouse, authenticate a tenant, or certify a release.
Rust source is read from the *same Git HEAD* even in sparse checkouts.
"""
from __future__ import annotations

import ast
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
import re
import subprocess
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
CAPTURE_SOURCE = ROOT / "posthog/api/capture.py"
INGESTION_SOURCE = ROOT / "posthog/settings/ingestion.py"
RUST = "rust/capture/src/v1/"


@lru_cache(maxsize=5)
def rust_source(relative: str) -> str:
    if relative not in (
        "constants.rs", "analytics/constants.rs",
        "analytics/types.rs", "analytics/response.rs",
        "analytics/router.rs",
    ):
        raise ValueError("Rust source must be an allowlisted literal file")
    p = subprocess.run(
        ["git", "-c", "maintenance.auto=false", "show",
         "HEAD:" + RUST + relative],
        cwd=ROOT, text=True, capture_output=True, timeout=15, check=False,
    )
    if p.returncode or not p.stdout:
        raise AssertionError("Rust Capture-v1 source not present in same HEAD")
    return p.stdout


def python_function(name: str, namespace: dict):
    module = ast.parse(CAPTURE_SOURCE.read_text())
    found = [
        node for node in module.body if isinstance(node, ast.FunctionDef)
        and node.name == name
    ]
    if len(found) != 1:
        raise AssertionError(f"Exactly one production function expected: {name}")
    found[0].decorator_list = []
    tree = ast.Module(
        body=[
            ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
            found[0],
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(CAPTURE_SOURCE), "exec"), namespace)
    return namespace[name]


def rust_string_constant(source: str, name: str) -> str:
    match = re.search(
        r"\b(?:pub(?:\(super\))?\s+)?const\s+" +
        re.escape(name) + r"\s*:\s*&str\s*=\s*\"([^\"]+)\";",
        source,
    )
    if not match:
        raise AssertionError(f"Rust constant unavailable: {name}")
    return match.group(1)


def rust_struct_fields(source: str, name: str) -> set[str]:
    pattern = r"pub struct " + re.escape(name) + r"\s*\{(.*?)\n\}"
    match = re.search(pattern, source, flags=re.DOTALL)
    if not match:
        raise AssertionError(f"Rust struct unavailable: {name}")
    return set(re.findall(r"\bpub\s+(\w+)\s*:", match.group(1)))


def producer_literal_dict_keys(function_name: str, target: str) -> set[str]:
    module = ast.parse(CAPTURE_SOURCE.read_text())
    func = next(node for node in module.body if isinstance(node, ast.FunctionDef)
                and node.name == function_name)
    fields: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            destinations = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if any(isinstance(dest, ast.Name) and dest.id == target for dest in destinations):
                if isinstance(value, ast.Dict):
                    fields.update(key.value for key in value.keys if isinstance(key, ast.Constant)
                                  and isinstance(key.value, str))
        if isinstance(node, ast.Assign):
            for dest in node.targets:
                if (isinstance(dest, ast.Subscript) and isinstance(dest.value, ast.Name)
                    and dest.value.id == target and isinstance(dest.slice, ast.Constant)
                    and isinstance(dest.slice.value, str)):
                    fields.add(dest.slice.value)
    return fields


class CaptureRustWireContractWave109(unittest.TestCase):
    def test_analytics_endpoint_matches_first_party_django_settings(self):
        rust = rust_string_constant(rust_source("analytics/constants.rs"), "CAPTURE_V1_PATH")
        python = re.search(
            r'CAPTURE_V1_INTERNAL_ENDPOINT\s*=\s*os.getenv\([^,]+,\s*"([^"]+)"\)',
            INGESTION_SOURCE.read_text(),
        )
        self.assertIsNotNone(python)
        self.assertEqual(rust, python.group(1))

    def test_ai_endpoint_matches_first_party_django_settings(self):
        rust = rust_string_constant(rust_source("analytics/constants.rs"), "CAPTURE_V1_AI_PATH")
        python = re.search(
            r'CAPTURE_V1_AI_INTERNAL_ENDPOINT\s*=\s*os.getenv\([^,]+,\s*"([^"]+)"\)',
            INGESTION_SOURCE.read_text(),
        )
        self.assertIsNotNone(python)
        self.assertEqual(rust, python.group(1))
        self.assertNotEqual(rust, "/i/v1/analytics/events")

    def test_python_real_header_builder_satisfies_rust_required_headers(self):
        source = rust_source("constants.rs")
        match = re.search(r"const REQUIRED_HEADERS[^=]*=\s*&\[(.*?)\];", source, re.DOTALL)
        self.assertIsNotNone(match)
        named = re.findall(r'POSTHOG_[A-Z_]+', match.group(1))
        plain = re.findall(r'"([^"]+)"', match.group(1))
        rust_required = {rust_string_constant(source, name).lower() for name in named}
        rust_required.update(header.lower() for header in plain)
        py_source = CAPTURE_SOURCE.read_text()
        sdk_match = re.search(r'^SDK_INFO\s*=\s*"([^"]+)"', py_source, re.MULTILINE)
        self.assertIsNotNone(sdk_match)
        make = python_function("_build_v1_headers", {
            "SDK_INFO": sdk_match.group(1), "uuid4": uuid4,
            "datetime": datetime, "UTC": UTC,
        })
        headers = make("synthetic_token", 2)
        self.assertTrue(rust_required.issubset({name.lower() for name in headers}))
        self.assertEqual(headers["User-Agent"], "flind-capture-v1-internal/1.0")
        self.assertEqual(headers["PostHog-Sdk-Info"], headers["User-Agent"])
        self.assertEqual(headers["PostHog-Attempt"], "2")
        self.assertEqual(headers["Authorization"], "Bearer synthetic_token")
        self.assertNotIn("synthetic_token", headers["User-Agent"])

    def test_retry_headers_and_response_shapes_agree(self):
        src = rust_source("analytics/response.rs")
        self.assertIn('outer.serialize_field("results"', src)
        self.assertIn('state.serialize_field("result", &self.result)', src)
        self.assertIn("headers.insert(header::RETRY_AFTER", src)
        producer = CAPTURE_SOURCE.read_text()
        self.assertIn('body.get("results", {})', producer)
        self.assertIn('entry.get("result")', producer)
        self.assertIn('resp.headers.get("Retry-After")', producer)

    def test_rust_explicit_statuses_equal_python_known_outcomes(self):
        rust = rust_source("analytics/types.rs")
        match = re.search(r"pub enum EventResult\s*\{(.*?)\n\}", rust, re.DOTALL)
        self.assertIsNotNone(match)
        statuses = set(re.findall(r"^\s*(Ok|Drop|Warning|Retry),", match.group(1), re.MULTILINE))
        python_tree = ast.parse(CAPTURE_SOURCE.read_text())
        values = [
            node.value for node in python_tree.body
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "_KNOWN_RESULT_STATUSES"
                for target in node.targets
            )
        ]
        self.assertEqual(len(values), 1)
        self.assertIsInstance(values[0], ast.Call)
        py_statuses = set(ast.literal_eval(values[0].args[0]))
        self.assertEqual({name.lower() for name in statuses}, py_statuses)
        self.assertEqual(py_statuses, {"ok", "drop", "warning", "retry"})

    def test_rust_batch_envelope_matches_python_production_payload(self):
        rust_fields = rust_struct_fields(rust_source("analytics/types.rs"), "Batch")
        python_fields = producer_literal_dict_keys("prepare_capture_internal_batch", "payload")
        self.assertEqual(rust_fields, python_fields)
        self.assertEqual(rust_fields, {"created_at", "historical_migration", "capture_internal", "batch"})

    def test_rust_event_fields_match_production_python_entry(self):
        rust_fields = rust_struct_fields(rust_source("analytics/types.rs"), "Event")
        py_fields = producer_literal_dict_keys("prepare_capture_internal_batch", "entry")
        self.assertEqual(rust_fields, py_fields)
        self.assertEqual(len(rust_fields), 8)

    def test_python_options_match_rust_options(self):
        rust_fields = rust_struct_fields(rust_source("analytics/types.rs"), "Options")
        py_tree = ast.parse(CAPTURE_SOURCE.read_text())
        options = [
            node.value for node in py_tree.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            and node.target.id == "_OPTIONS_TO_LEGACY_PROPERTY"
        ]
        self.assertEqual(len(options), 1)
        py_keys = set(ast.literal_eval(options[0]))
        self.assertEqual(rust_fields, py_keys)

    def test_rust_registers_separate_analytics_ai_routers(self):
        source = rust_source("analytics/router.rs")
        self.assertIn("pub fn routes()", source)
        self.assertIn("pub fn ai_routes()", source)
        self.assertIn("CAPTURE_V1_AI_PATH", source)
        self.assertIn("CAPTURE_V1_PATH", source)

    def test_python_malformed_result_never_default_ack(self):
        py = CAPTURE_SOURCE.read_text()
        self.assertIn('raw_status = entry.get("result")', py)
        self.assertIn('if not isinstance(raw_status, str) or raw_status not in _KNOWN_RESULT_STATUSES:', py)
        self.assertIn('aggregated[uid] = {"result": "unaccounted"}', py)

    def test_git_head_matches_sparse_workspace(self):
        # Avoid comparing stale files in /tmp to a newer main. All rust reads are
        # pinned to the same HEAD as this first-party Python source checkout.
        rev = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=8,
        )
        self.assertEqual(rev.returncode, 0)
        self.assertRegex(rev.stdout.strip(), r"^[a-f0-9]{40}$")

    def test_does_not_claim_rust_binary_executed(self):
        self.assertIn("DOES NOT compile or execute Rust", __doc__)


if __name__ == "__main__":
    unittest.main()
