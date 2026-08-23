"""
Testes de DeviceMetricsETL contra um Postgres real descartável (ver
conftest.py) — sem mocks, mesmo padrão do resto do projeto.
"""

from datetime import UTC, datetime, timedelta

from infra.database.db_connection_handler import db_connection_handler
from models import Device, MetricDefinition, MetricHistory, MetricValueType, Subnet
from repositories.metric_history_repository import MetricHistoryRepository

from .device_metrics_etl import DeviceMetricsETL


def _seed_device_and_metric(session) -> tuple[int, int]:
    subnet = Subnet(cidr="0.0.0.0/32")
    session.add(subnet)
    session.flush()
    device = Device(ip="10.0.0.1", mac="00:00:00:00:00:01", subnet_id=subnet.id)
    session.add(device)
    definition = MetricDefinition(
        key="cpu_load", oid="1.2.3", name="CPU Load", unit="%", value_type=MetricValueType.GAUGE
    )
    session.add(definition)
    session.flush()
    return device.id, definition.id


def test_build_series_returns_empty_points_for_unknown_metric_key():
    with db_connection_handler.get_session() as session:
        device_id, _definition_id = _seed_device_and_metric(session)

        series = DeviceMetricsETL(session).build_series(device_id, "does_not_exist", range_hours=1)
        metric_key, metric_name, unit, points = (
            series.metric_key,
            series.metric_name,
            series.unit,
            series.points,
        )

    assert (metric_key, metric_name, unit, points) == ("does_not_exist", "does_not_exist", None, [])


def test_build_series_returns_points_within_range_sorted_ascending():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed_device_and_metric(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=now - timedelta(minutes=30),
                    value_numeric=10.0,
                ),
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=now - timedelta(minutes=20),
                    value_numeric=20.0,
                ),
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=now - timedelta(minutes=10),
                    value_numeric=30.0,
                ),
            ]
        )

        series = DeviceMetricsETL(session).build_series(device_id, "cpu_load", range_hours=1)
        metric_name, unit, values = series.metric_name, series.unit, [p.v for p in series.points]

    assert (metric_name, unit, values) == ("CPU Load", "%", [10.0, 20.0, 30.0])


def test_build_series_excludes_points_older_than_range():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed_device_and_metric(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=now - timedelta(hours=2),
                    value_numeric=999.0,
                ),
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=now - timedelta(minutes=10),
                    value_numeric=42.0,
                ),
            ]
        )

        series = DeviceMetricsETL(session).build_series(device_id, "cpu_load", range_hours=1)
        values = [p.v for p in series.points]

    assert values == [42.0]
