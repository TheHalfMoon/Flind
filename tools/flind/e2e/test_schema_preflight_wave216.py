import unittest

from tools.flind.e2e.schema_preflight_wave216 import (
    POSTGRES_REQUIRED, CLICKHOUSE_REQUIRED, missing_tables,
)
from tools.flind.e2e.verify_wave216 import assert_owned_service

class FlindWave216SchemaAdmissionTests(unittest.TestCase):
    def test_clean_original_schemas_are_admitted(self):
        self.assertEqual(missing_tables(POSTGRES_REQUIRED, POSTGRES_REQUIRED), [])
        self.assertEqual(missing_tables(CLICKHOUSE_REQUIRED, CLICKHOUSE_REQUIRED), [])

    def test_empty_database_is_explicitly_not_qualified(self):
        self.assertEqual(set(missing_tables(POSTGRES_REQUIRED, set())), POSTGRES_REQUIRED)
        self.assertEqual(set(missing_tables(CLICKHOUSE_REQUIRED, set())), CLICKHOUSE_REQUIRED)

    def test_foreign_project_container_fails_closed(self):
        item = {"Config":{"Labels":{"com.docker.compose.project":"zyara",
                "com.docker.compose.service":"postgres"}},
                "State":{"Running":True,"Health":{"Status":"healthy"}},
                "NetworkSettings":{"Ports":{"5432/tcp":[
                    {"HostIp":"127.0.0.1","HostPort":"15439"}]}}}
        with self.assertRaisesRegex(AssertionError, 'wrong Compose project'):
            assert_owned_service("postgres", item)

    def test_non_loopback_mapping_fails_closed(self):
        item = {"Config":{"Labels":{"com.docker.compose.project":"flindwave216",
                "com.docker.compose.service":"postgres"}},
                "State":{"Running":True,"Health":{"Status":"healthy"}},
                "NetworkSettings":{"Ports":{"5432/tcp":[
                    {"HostIp":"0.0.0.0","HostPort":"15439"}]}}}
        with self.assertRaisesRegex(AssertionError, 'beyond loopback'):
            assert_owned_service("postgres", item)

if __name__ == "__main__":
    unittest.main()
