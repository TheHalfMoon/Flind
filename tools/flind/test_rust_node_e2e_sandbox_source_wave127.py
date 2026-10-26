"""Wave127 static guards around the actual destructive Rust/Node E2E suite."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TEST = ROOT / "nodejs/tests/service-e2e/rust-ingestion-consumer.serial.test.ts"
ADMISSION = ROOT / "nodejs/tests/service-e2e/rust-node-sandbox-admission.ts"
LAUNCH = ROOT / "nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs"


class RustNodeSandboxSourceWave127(unittest.TestCase):
    def test_config_is_checked_before_database_reset_in_before_all(self):
        source = TEST.read_text()
        self.assertIn("assertIsolatedRustNodeE2EAlreadyPrepared(process.env)", source)
        self.assertIn("const sandbox = assertIsolatedRustNodeE2EAlreadyPrepared(process.env)", source)
        self.assertIn("configureParentTestEnv()", source)
        self.assertLess(source.index("configureParentTestEnv()"), source.index("await resetTestDatabase()"))

    def test_service_e2e_no_longer_supplies_shared_default_hosts(self):
        source = TEST.read_text()
        for unsafe in (
            "postgres://posthog:posthog@localhost:5432",
            "KAFKA_HOSTS: 'localhost:9092'",
            "CLICKHOUSE_DATABASE: 'posthog_test'",
            "REDIS_URL: 'redis://127.0.0.1'",
        ):
            self.assertNotIn(unsafe, source)

    def test_all_downstream_worker_connections_derive_from_isolated_env(self):
        source = TEST.read_text()
        self.assertIn("KAFKA_HOSTS: E2E_KAFKA_BOOTSTRAP", source)
        self.assertIn("KAFKA_PRODUCER_METADATA_BROKER_LIST: E2E_KAFKA_BOOTSTRAP", source)
        self.assertIn("CLICKHOUSE_DATABASE: E2E_CLICKHOUSE_DATABASE", source)
        self.assertIn("REDIS_URL: E2E_REDIS_URL", source)
        self.assertIn("const POSTGRES_URL = (process.env.FLIND_E2E_POSTGRES_BASE_URL", source)

    def test_launcher_refuses_unverified_and_ambient_shell_secrets(self):
        source = LAUNCH.read_text()
        self.assertIn("isolatedRustNodeE2E(process.env)", source)
        self.assertIn("const processEnv = {}", source)
        self.assertIn("key.startsWith('FLIND_E2E_')", source)
        self.assertIn("Object.assign(processEnv", source)
        self.assertIn("...sandbox.serviceEnv", source)
        self.assertIn("jest.serial.config.js", source)
        self.assertIn("runInBand", source)
        self.assertIn("process.argv.includes('--dry-run')", source)

    def test_admission_enforces_explicit_ownership_and_unique_test_db(self):
        source = ADMISSION.read_text()
        self.assertIn("I_OWN_THESE_DISPOSABLE_FLIND_TEST_DATABASES", source)
        self.assertIn("flind_test_[a-z0-9]{12,}", source)
        for shared_port in ("5432", "9092", "6379"):
            self.assertIn(shared_port, source)
        self.assertIn("new Set([Number(postgres.port), kafkaPort, Number(redis.port), clickhousePort])", source)


if __name__ == "__main__":
    unittest.main()
