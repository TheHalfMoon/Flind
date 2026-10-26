"""Wave128 ClickHouse endpoint admission and real native service evidence."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.flind import qualify_node_clickhouse_private_port_wave128 as q


class NodePrivateClickhouseWave128(unittest.TestCase):
    def test_real_process_owned_clickhouse_sql_and_first_party_node_origin(self):
        if not q.BINARY.is_file():
            self.skipTest("Supported private ClickHouse25.12 binary unavailable")
        observed = q.qualify()
        self.assertTrue(observed["first_party_node_clickhouse_port_real_sql_qualified"], observed.get("blocker"))
        self.assertTrue(observed["actual_node_test_executed"])
        self.assertTrue(observed["actual_private_clickhouse_started"])
        self.assertTrue(observed["private_server_process_cleanup_completed"])
        child = observed["node_http_receipt"]
        self.assertTrue(child["node_reached_actual_clickhouse"])
        self.assertTrue(child["real_clickhouse_sql_readback"])
        self.assertEqual(child["native_node_exit"], 0)
        self.assertFalse(observed["full_clickhouse_helper_import_qualified"])
        self.assertFalse(observed["production_rust_node_clickhouse_e2e_qualified"])
        self.assertFalse(observed["release_qualified"])

    def test_exact_same_helper_origin_used_for_client_and_health(self):
        source = (q.ROOT / "nodejs/tests/helpers/clickhouse.ts").read_text()
        self.assertIn("import { clickhouseTestHttpOrigin } from './clickhouse-http-endpoint'", source)
        self.assertIn("url: clickhouseTestHttpOrigin(process.env)", source)
        self.assertIn("clickhouseTestHttpOrigin(process.env)}/ping", source)
        self.assertNotIn("http://localhost:8123/ping", source)

    def test_sandbox_requires_nondefault_owned_clickhouse_http_port(self):
        src = (q.ROOT / "nodejs/tests/service-e2e/rust-node-sandbox-admission.ts").read_text()
        self.assertIn("FLIND_E2E_CLICKHOUSE_HTTP_PORT", src)
        self.assertIn("localPort(env.FLIND_E2E_CLICKHOUSE_HTTP_PORT ?? '', 'ClickHouse', 8123)", src)
        self.assertIn("CLICKHOUSE_HTTP_PORT: String(clickhousePort)", src)
        self.assertIn("clickhousePort]).size !== 4", src)
        self.assertIn("[5432, 9092, 6379, 8123].includes(port)", src)

    def test_unavailable_binary_refuses_qualification(self):
        with patch.object(q, "BINARY", Path("/nonexistent/flind-clickhouse")):
            failed = q.qualify()
        self.assertFalse(failed["first_party_node_clickhouse_port_real_sql_qualified"])
        self.assertFalse(failed["release_qualified"])
        self.assertIn("blocker", failed)

    def test_unsafe_default_port_does_not_start_database_or_node(self):
        result = q.active_server_probe(8123)
        self.assertFalse(result["actual_node_endpoint_helper_exercised"])
        self.assertFalse(result["node_reached_actual_clickhouse"])
        self.assertIn("blocker", result)


if __name__ == "__main__":
    unittest.main()
