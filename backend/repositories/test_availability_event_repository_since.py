"""
Testes de AvailabilityEventRepository.list_by_device_since/list_since contra
um Postgres real descartável (ver conftest.py) — sem mocks.

Ambos precisam trazer eventos que ainda se sobrepõem à janela [since, agora],
inclusive um evento aberto (ended_at nulo) que começou antes de `since`.
"""

from datetime import UTC, datetime, timedelta

from infra.database.db_connection_handler import db_connection_handler
from models import Device, DeviceStatus, Subnet

from .availability_event_repository import AvailabilityEventRepository
from .device_repository import DeviceRepository
from .subnet_repository import SubnetRepository


def _seed_device(session, ip: str, mac: str) -> int:
    subnet = SubnetRepository(session).save(Subnet(cidr="0.0.0.0/32"))
    return DeviceRepository(session).save_many([Device(ip=ip, mac=mac, subnet_id=subnet.id)])[0].id


def test_list_by_device_since_includes_open_event_started_before_cutoff():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session, "10.0.0.1", "00:00:00:00:00:01")
        repo = AvailabilityEventRepository(session)
        repo.open_event(device_id, DeviceStatus.ONLINE, now - timedelta(hours=5))

        events = repo.list_by_device_since(device_id, now - timedelta(hours=1))
        ended_ats = [e.ended_at for e in events]

    assert ended_ats == [None]


def test_list_by_device_since_excludes_event_closed_before_cutoff():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session, "10.0.0.1", "00:00:00:00:00:01")
        repo = AvailabilityEventRepository(session)
        repo.open_event(device_id, DeviceStatus.OFFLINE, now - timedelta(hours=5))
        repo.close_open_event(device_id, now - timedelta(hours=4))
        repo.open_event(device_id, DeviceStatus.ONLINE, now - timedelta(hours=4))

        events = repo.list_by_device_since(device_id, now - timedelta(hours=1))
        statuses = [e.status for e in events]

    assert statuses == [DeviceStatus.ONLINE]


def test_list_since_includes_events_from_every_device():
    now = datetime.now(UTC)
    with db_connection_handler.get_session() as session:
        device_a = _seed_device(session, "10.0.0.1", "00:00:00:00:00:01")
        device_b = _seed_device(session, "10.0.0.2", "00:00:00:00:00:02")
        repo = AvailabilityEventRepository(session)
        repo.open_event(device_a, DeviceStatus.ONLINE, now - timedelta(hours=1))
        repo.open_event(device_b, DeviceStatus.OFFLINE, now - timedelta(hours=1))

        events = repo.list_since(now - timedelta(hours=2))
        device_ids = {e.device_id for e in events}

    assert device_ids == {device_a, device_b}
