"""
Testes de upsert_many_by_mac() contra um Postgres real descartável (ver
conftest.py) — sem mocks.
"""

from datetime import UTC, datetime

from infra.database.db_connection_handler import db_connection_handler
from models import Device, DeviceStatus, Subnet

from .device_repository import DeviceRepository
from .subnet_repository import SubnetRepository


def _seed_subnet(session) -> int:
    return SubnetRepository(session).save(Subnet(cidr="0.0.0.0/32")).id


def test_upsert_by_mac_updates_existing_device_instead_of_duplicating():
    with db_connection_handler.get_session() as session:
        subnet_id = _seed_subnet(session)
        repo = DeviceRepository(session)

        first_id = repo.upsert_many_by_mac(
            [Device(ip="10.0.0.1", mac="aa:bb:cc:dd:ee:ff", vendor="Acme", subnet_id=subnet_id)]
        )[0].id

        second = repo.upsert_many_by_mac(
            [Device(ip="10.0.0.2", mac="aa:bb:cc:dd:ee:ff", vendor="Acme", subnet_id=subnet_id)]
        )[0]
        second_id, second_ip = second.id, second.ip

        all_ids = [d.id for d in repo.list_all()]

    assert second_id == first_id
    assert second_ip == "10.0.0.2"
    assert all_ids == [first_id]


def test_upsert_by_mac_inserts_new_device_when_mac_is_unseen():
    with db_connection_handler.get_session() as session:
        subnet_id = _seed_subnet(session)
        repo = DeviceRepository(session)

        repo.upsert_many_by_mac(
            [Device(ip="10.0.0.1", mac="aa:bb:cc:dd:ee:01", subnet_id=subnet_id)]
        )
        repo.upsert_many_by_mac(
            [Device(ip="10.0.0.2", mac="aa:bb:cc:dd:ee:02", subnet_id=subnet_id)]
        )

        macs = {d.mac for d in repo.list_all()}

    assert macs == {"aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:02"}


def test_upsert_by_mac_preserves_status_and_polling_state_on_update():
    with db_connection_handler.get_session() as session:
        subnet_id = _seed_subnet(session)
        repo = DeviceRepository(session)

        device_id = repo.upsert_many_by_mac(
            [Device(ip="10.0.0.1", mac="aa:bb:cc:dd:ee:ff", subnet_id=subnet_id)]
        )[0].id
        checked_at = datetime.now(UTC)
        repo.record_poll_result(
            device_id,
            status=DeviceStatus.ONLINE,
            consecutive_failures=0,
            poll_interval_seconds=60,
            next_poll_at=checked_at,
            last_checked_at=checked_at,
        )

        updated = repo.upsert_many_by_mac(
            [Device(ip="10.0.0.9", mac="aa:bb:cc:dd:ee:ff", subnet_id=subnet_id)]
        )[0]
        updated_status, updated_checked_at = updated.status, updated.last_checked_at

    assert updated_status == DeviceStatus.ONLINE
    assert updated_checked_at.replace(tzinfo=UTC) == checked_at
