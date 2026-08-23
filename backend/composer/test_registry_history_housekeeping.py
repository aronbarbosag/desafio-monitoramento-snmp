"""
Testes de integração de run_housekeeping_cycle() contra um Postgres real
descartável (ver conftest.py) — sem mocks.
"""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import pytest

from infra.database.db_connection_handler import db_connection_handler
from models import Device, MetricDefinition, MetricHistory, MetricValueType, Subnet
from repositories.metric_history_repository import MetricHistoryRepository
from repositories.metric_trend_repository import MetricTrendRepository

from . import registry_history_housekeeping as rhh
from .registry_history_housekeeping import run_housekeeping_cycle


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


def test_housekeeping_cycle_rolls_up_and_prunes_old_numeric_metric():
    old_moment = datetime.now(UTC) - timedelta(days=rhh.RAW_RETENTION_DAYS, hours=2)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=old_moment,
                    value_numeric=99.0,
                )
            ]
        )

    run_housekeeping_cycle()

    with db_connection_handler.get_session() as session:
        raw_remaining = len(MetricHistoryRepository(session).list_by_device(device_id, limit=10))
        trends = MetricTrendRepository(session).list_by_device(device_id)
        trend_count = len(trends)
        trend_avg = trends[0].value_avg if trends else None

    assert raw_remaining == 0
    assert trend_count == 1
    assert trend_avg == 99.0


def test_housekeeping_cycle_prunes_old_text_metric_without_creating_trend():
    old_moment = datetime.now(UTC) - timedelta(days=rhh.RAW_RETENTION_DAYS, hours=2)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=old_moment,
                    value_text="Ready",
                )
            ]
        )

    run_housekeeping_cycle()

    with db_connection_handler.get_session() as session:
        raw_remaining = len(MetricHistoryRepository(session).list_by_device(device_id, limit=10))
        trend_count = len(MetricTrendRepository(session).list_by_device(device_id))

    assert raw_remaining == 0
    assert trend_count == 0


def test_housekeeping_cycle_keeps_recent_raw_rows():
    recent_moment = datetime.now(UTC) - timedelta(hours=1)
    with db_connection_handler.get_session() as session:
        device_id, definition_id = _seed(session)
        MetricHistoryRepository(session).save_many(
            [
                MetricHistory(
                    device_id=device_id,
                    metric_definition_id=definition_id,
                    collected_at=recent_moment,
                    value_numeric=5.0,
                )
            ]
        )

    run_housekeeping_cycle()

    with db_connection_handler.get_session() as session:
        raw_remaining = len(MetricHistoryRepository(session).list_by_device(device_id, limit=10))

    assert raw_remaining == 1


@pytest.mark.asyncio
async def test_run_forever_keeps_looping_after_a_cycle_raises(monkeypatch):
    call_count = 0

    def flaky_cycle() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("ciclo falhou de propósito, pra testar a resiliência")

    monkeypatch.setattr(rhh, "run_housekeeping_cycle", flaky_cycle)
    monkeypatch.setattr(rhh, "TICK_INTERVAL_SECONDS", 0)

    task = asyncio.create_task(rhh.run_forever())
    try:
        for _ in range(1000):
            if call_count >= 2:
                break
            await asyncio.sleep(0)
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    assert call_count >= 2
