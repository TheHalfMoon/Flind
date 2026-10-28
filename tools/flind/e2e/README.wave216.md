# Wave 216: isolated Flind data-service setup

This launches only three Docker services in the unique flindwave216 Compose
project. Never use the ordinary development Compose file or another
project's database.

PostgreSQL: 127.0.0.1:15439
Redis: 127.0.0.1:16380
ClickHouse: http://127.0.0.1:18124

PostgreSQL databases: test_posthog, test_persons,
test_behavioral_cohorts, test_cyclotron_node.
ClickHouse database: flind_test_wave216abc123.
Credentials are synthetic throwaway local-only test values.

From this directory:

    docker compose -p flindwave216 -f compose.wave216.yaml config -q
    docker compose -p flindwave216 -f compose.wave216.yaml up -d
    docker compose -p flindwave216 -f compose.wave216.yaml ps

To stop only this isolated project:

    docker compose -p flindwave216 -f compose.wave216.yaml stop

Only after verifying ownership, dispose its ephemeral volumes:

    docker compose -p flindwave216 -f compose.wave216.yaml down -v

No Docker-wide cleanup or default service port is authorized.
Full Kafka -> Rust -> production Node -> ClickHouse requires additional
migrations, Kafka engine and end-to-end Jest qualification.
This provision alone is not a release qualification.

Repository PRIVATE; GitHub Actions disabled; Release NO-GO.
