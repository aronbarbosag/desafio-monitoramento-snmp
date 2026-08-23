"""
Testes de MetricHistoryRepository.list_by_device_and_metric_since contra um
Postgres real descartável (ver conftest.py) — sem mocks.
"""

from datetime import UTC, datetime, timedelta

from infra.database.db_connection_handler import db_connection_handler
from models import Device, MetricDefinition, MetricHistory, MetricValueType, Subnet

from .metric_history_repository import MetricHistoryRepository


def _seed(session) -> tuple[int, int, int]:
    subnet = Subnet(cidr="0.0.0.0/32")
    session.add(subnet)
    session.flush()
    device = Device(ip="10.0.0.1", mac="00:00:00:00:00:01", subnet_id=subnet.id)
    session.add(device)
    cpu = MetricDefinition(
        key="cpu_load", oid="1.2.3", name="CPU Load", value_type=MetricValueType.GAUGE
    )
    mem = MetricDefinition(
        key="mem_used", oid="1.2.4", name="Memory Used", value_type=MetricValueType.GAUGE
    )
    session.add_all([cpu, mem])
    session.flush()
    return device.id, cpu.id, mem.id


def test_list_by_device_and_metric_since_filters_by_metric_key():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id, cpu_id, mem_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=cpu_id,
                    collected_at=now,
                    value_numeric=10.0,
                ),
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=mem_id,
                    collected_at=now,
                    value_numeric=99.0,
                ),
            ]
        )

        rows = MetricHistoryRepository(session).list_by_device_and_metric_since(
            device_id, "cpu_load", now - timedelta(hours=1)
        )
        values = [r.value_numeric for r in rows]

    assert values == [10.0]


def test_list_by_device_and_metric_since_excludes_rows_before_cutoff():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id, cpu_id, _mem_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=cpu_id,
                    collected_at=now - timedelta(hours=2),
                    value_numeric=1.0,
                ),
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=cpu_id,
                    collected_at=now - timedelta(minutes=1),
                    value_numeric=2.0,
                ),
            ]
        )

        rows = MetricHistoryRepository(session).list_by_device_and_metric_since(
            device_id, "cpu_load", now - timedelta(hours=1)
        )
        values = [r.value_numeric for r in rows]

    assert values == [2.0]


def test_list_by_device_and_metric_since_returns_empty_for_unknown_metric():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id, _cpu_id, _mem_id = _seed(session)

        rows = MetricHistoryRepository(session).list_by_device_and_metric_since(
            device_id, "does_not_exist", now - timedelta(hours=1)
        )

    assert rows == []
