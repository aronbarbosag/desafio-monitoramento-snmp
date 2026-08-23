"""
Testes de list_due_for_poll() contra um Postgres real descartável (ver
conftest.py) — sem mocks, mesma abordagem usada nos outros testes do projeto.
"""

from datetime import UTC, datetime, timedelta

from infra.database.db_connection_handler import db_connection_handler
from models import Device, Subnet

from .device_repository import DeviceRepository
from .subnet_repository import SubnetRepository


def _seed_device(session, *, snmp_community: str | None) -> Device:
    subnet = SubnetRepository(session).save(Subnet(cidr="0.0.0.0/32"))
    past = datetime.now(UTC) - timedelta(minutes=1)
    return DeviceRepository(session).save_many(
        [
            Device(
                ip="10.0.0.1",
                mac="00:00:00:00:00:00",
                subnet_id=subnet.id,
                snmp_community=snmp_community,
                next_poll_at=past,
            )
        ]
    )[0]


def test_list_due_for_poll_includes_device_without_snmp():
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session, snmp_community=None).id

        due_ids = [d.id for d in DeviceRepository(session).list_due_for_poll(datetime.now(UTC))]

    assert due_ids == [device_id]


def test_list_due_for_poll_includes_device_with_snmp():
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session, snmp_community="public").id

        due_ids = [d.id for d in DeviceRepository(session).list_due_for_poll(datetime.now(UTC))]

    assert due_ids == [device_id]
