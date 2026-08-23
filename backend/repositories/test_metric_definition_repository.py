"""
Testes de MetricDefinitionRepository contra um Postgres real descartável
(ver conftest.py) — sem mocks.
"""

from infra.database.db_connection_handler import db_connection_handler
from models import MetricDefinition, MetricValueType

from .metric_definition_repository import MetricDefinitionRepository


def test_list_static_excludes_dynamic_placeholder_oid():
    with db_connection_handler.get_session() as session:
        repo = MetricDefinitionRepository(session)
        repo.upsert_catalog(
            [
                MetricDefinition(
                    key="sys_uptime",
                    oid="1.3.6.1.2.1.1.3.0",
                    name="Uptime",
                    value_type=MetricValueType.COUNTER,
                )
            ]
        )
        repo.get_or_create("if_octets_eth0", name="eth0 octets", value_type=MetricValueType.GAUGE)

        static_keys = [d.key for d in repo.list_static()]

    assert static_keys == ["sys_uptime"]
