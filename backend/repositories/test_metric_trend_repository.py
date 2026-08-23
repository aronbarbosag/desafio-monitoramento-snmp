"""
Testes de MetricTrendRepository contra um Postgres real descartável (ver
conftest.py) — sem mocks.
"""

from datetime import UTC, datetime

from infra.database.db_connection_handler import db_connection_handler
from models import Device, MetricDefinition, MetricHistory, MetricValueType, Subnet
from repositories.metric_history_repository import MetricHistoryRepository

from .metric_trend_repository import MetricTrendRepository


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


def test_upsert_hourly_aggregates_computes_min_max_avg_count_for_closed_hour():
    closed_hour = datetime(2026, 1, 1, 10, tzinfo=UTC)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=closed_hour.replace(minute=m),
                    value_numeric=value,
                )
                for m, value in [(5, 10.0), (25, 20.0), (45, 30.0)]
            ]
        )

        created = MetricTrendRepository(session).upsert_hourly_aggregates(
            before=datetime(2026, 1, 1, 11, tzinfo=UTC)
        )

        trends = MetricTrendRepository(session).list_by_device(device_id)
        trend = trends[0]
        trend_min, trend_max, trend_avg, trend_count = (
            trend.value_min,
            trend.value_max,
            trend.value_avg,
            trend.sample_count,
        )

    assert created == 1
    assert (trend_min, trend_max, trend_avg, trend_count) == (10.0, 30.0, 20.0, 3)


def test_upsert_hourly_aggregates_ignores_current_open_hour():
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=datetime.now(UTC),
                    value_numeric=42.0,
                )
            ]
        )

        created = MetricTrendRepository(session).upsert_hourly_aggregates(
            before=datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        )
        trends = MetricTrendRepository(session).list_by_device(device_id)

    assert created == 0
    assert trends == []


def test_upsert_hourly_aggregates_ignores_text_only_metrics():
    closed_hour = datetime(2026, 1, 1, 10, tzinfo=UTC)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=closed_hour,
                    value_text="Ready",
                )
            ]
        )

        created = MetricTrendRepository(session).upsert_hourly_aggregates(
            before=datetime(2026, 1, 1, 11, tzinfo=UTC)
        )
        trends = MetricTrendRepository(session).list_by_device(device_id)

    assert created == 0
    assert trends == []


def test_upsert_hourly_aggregates_is_idempotent():
    closed_hour = datetime(2026, 1, 1, 10, tzinfo=UTC)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=closed_hour,
                    value_numeric=10.0,
                )
            ]
        )
        repo = MetricTrendRepository(session)
        before = datetime(2026, 1, 1, 11, tzinfo=UTC)

        repo.upsert_hourly_aggregates(before=before)
        repo.upsert_hourly_aggregates(before=before)

        trend_count = len(repo.list_by_device(device_id))

    assert trend_count == 1
