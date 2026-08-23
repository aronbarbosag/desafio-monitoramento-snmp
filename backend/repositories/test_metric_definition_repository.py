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


def test_get_by_key_returns_matching_definition():
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

        found = repo.get_by_key("sys_uptime")
        found_name = found.name if found else None

    assert found_name == "Uptime"


def test_get_by_key_returns_none_for_unknown_key():
    with db_connection_handler.get_session() as session:
        found = MetricDefinitionRepository(session).get_by_key("does_not_exist")

    assert found is None


def test_get_or_create_accepts_a_long_key():
    """Regressão: interfaces virtuais do Windows (Hyper-V) geram nomes bem
    longos, e a key vira um slug deles — key era VARCHAR(64), curta demais
    (Postgres rejeita com StringDataRightTruncation)."""
    long_key = "if_" + "hyper_v_virtual_switch_extension_adapter_2_extension_filter" * 2

    with db_connection_handler.get_session() as session:
        repo = MetricDefinitionRepository(session)
        definition = repo.get_or_create(
            long_key, name="long name", value_type=MetricValueType.GAUGE
        )
        definition_key = definition.key

    assert definition_key == long_key
