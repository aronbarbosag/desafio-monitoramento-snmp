"""
Testes de AvailabilityETL contra um Postgres real descartável (ver
conftest.py) — sem mocks.
"""

from datetime import UTC, datetime, timedelta

import pytest

from infra.database.db_connection_handler import db_connection_handler
from models import Device, DeviceStatus, Subnet
from repositories.availability_event_repository import AvailabilityEventRepository
from repositories.device_repository import DeviceRepository
from repositories.subnet_repository import SubnetRepository

from .availability_etl import AvailabilityETL


def _seed_device(
    session, *, ip: str = "10.0.0.1", mac: str = "00:00:00:00:00:01", snmp_supported: bool = False
) -> int:
    subnet = SubnetRepository(session).save(Subnet(cidr="0.0.0.0/32"))
    return (
        DeviceRepository(session)
        .save_many([Device(ip=ip, mac=mac, subnet_id=subnet.id, snmp_supported=snmp_supported)])[0]
        .id
    )


def test_summary_returns_zero_for_device_without_events():
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session)

        summary = AvailabilityETL(session).summary(device_id, range_hours=1)
        result = (summary.availability_pct, summary.downtime_seconds, summary.mttr_seconds)

    assert result == (0.0, 0, None)


def test_summary_computes_availability_downtime_and_mttr():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session)
        repo = AvailabilityEventRepository(session)
        offline_start = now - timedelta(hours=2)
        offline_end = now - timedelta(hours=1, minutes=30)
        repo.open_event(device_id, DeviceStatus.OFFLINE, offline_start)
        repo.close_open_event(device_id, offline_end)
        repo.open_event(device_id, DeviceStatus.ONLINE, offline_end)

        summary = AvailabilityETL(session).summary(device_id, range_hours=2)
        pct, downtime, mttr = (
            summary.availability_pct,
            summary.downtime_seconds,
            summary.mttr_seconds,
        )

    # Janela de 2h: ~30min offline (evento fechado) + ~1h30 online (evento
    # ainda aberto) — tolerância pequena por causa do tempo real decorrido
    # entre `now` (seed) e o `datetime.now(UTC)` chamado dentro do ETL.
    assert pct == pytest.approx(75.0, abs=1.0)
    assert downtime == pytest.approx(1800, abs=5)
    assert mttr == pytest.approx(1800.0, abs=5)


def test_dashboard_summary_counts_devices_and_averages_availability():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        online_device = _seed_device(
            session, ip="10.0.0.1", mac="00:00:00:00:00:01", snmp_supported=True
        )
        offline_device = _seed_device(
            session, ip="10.0.0.2", mac="00:00:00:00:00:02", snmp_supported=False
        )
        DeviceRepository(session).record_poll_result(
            online_device,
            status=DeviceStatus.ONLINE,
            consecutive_failures=0,
            poll_interval_seconds=60,
            next_poll_at=now,
            last_checked_at=now,
        )
        DeviceRepository(session).record_poll_result(
            offline_device,
            status=DeviceStatus.OFFLINE,
            consecutive_failures=1,
            poll_interval_seconds=60,
            next_poll_at=now,
            last_checked_at=now,
        )
        events = AvailabilityEventRepository(session)
        events.open_event(online_device, DeviceStatus.ONLINE, now - timedelta(hours=1))
        events.open_event(offline_device, DeviceStatus.OFFLINE, now - timedelta(hours=1))

        summary = AvailabilityETL(session).dashboard_summary(range_hours=2)
        counts = (
            summary.total_devices,
            summary.online,
            summary.offline,
            summary.unknown,
            summary.snmp_supported,
            summary.open_problems,
        )
        avg_pct = summary.avg_availability_pct

    assert counts == (2, 1, 1, 0, 1, 1)
    # online_device: 1h online de uma janela de 2h -> 50%; offline_device: 0%.
    assert avg_pct == pytest.approx(25.0, abs=2.0)
