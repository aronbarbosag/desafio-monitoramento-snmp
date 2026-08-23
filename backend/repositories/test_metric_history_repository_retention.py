"""
Testes de MetricHistoryRepository.delete_older_than contra um Postgres real
descartável (ver conftest.py) — sem mocks.
"""

from datetime import UTC, datetime, timedelta

from infra.database.db_connection_handler import db_connection_handler
from models import Device, MetricDefinition, MetricHistory, MetricValueType, Subnet

from .metric_history_repository import MetricHistoryRepository


def _seed(session) -> tuple[int, int]:
    subnet = Subnet(cidr="0.0.0.0/32")
    session.add(subnet)
    session.flush()
    device = Device(ip="10.0.0.1", mac="00:00:00:00:00:01", subnet_id=subnet.id)
    session.add(device)
    definition = MetricDefinition(
        key="cpu_load", oid="1.2.3", name="CPU Load", value_type=MetricValueType.GAUGE
    )
    session.add(definition)
    session.flush()
    return device.id, definition.id


def test_delete_older_than_removes_only_rows_before_cutoff():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        repo = MetricHistoryRepository(session)
        repo.save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=now - timedelta(days=10),
                    value_numeric=1.0,
                ),
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=now - timedelta(days=1),
                    value_numeric=2.0,
                ),
            ]
        )

        deleted = repo.delete_older_than(now - timedelta(days=7))
        remaining = repo.list_by_device(device_id, limit=10)
        remaining_count = len(remaining)

    assert deleted == 1
    assert remaining_count == 1
