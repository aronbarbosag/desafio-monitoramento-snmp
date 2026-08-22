"""
Testes de integração REAIS de run_ip_and_snmp_scan(ipscan=False) — o modo que
pula o ARP e sonda via SNMP direto os devices já existentes no banco.

Nada aqui é mockado: os pacotes SNMP saem de verdade pela rede contra o
device configurado em SNMP_TEST_TARGET. O modo ipscan=True (que depende de
ARP/Npcap) já é coberto indiretamente pelos testes de IpScanService e
SnmpScanService — aqui o foco é só o novo comportamento de reuso do banco.
"""

import os

import pytest

from infra.database.db_connection_handler import db_connection_handler
from models import Base, Device, Subnet
from repositories.device_repository import DeviceRepository
from repositories.subnet_repository import SubnetRepository

from .registry_devices import run_ip_and_snmp_scan

# Faixa TEST-NET-2 (RFC 5737): reservada para documentação, nunca roteada.
UNUSED_IP = "198.51.100.2"


def _seed_device(ip: str) -> int:
    Base.metadata.create_all(db_connection_handler.get_engine())
    with db_connection_handler.get_session() as session:
        subnet = SubnetRepository(session).save(Subnet(cidr="0.0.0.0/32"))
        device = DeviceRepository(session).save_many(
            [Device(ip=ip, mac="00:00:00:00:00:00", subnet_id=subnet.id)]
        )[0]
        return device.id


@pytest.mark.asyncio
async def test_ipscan_false_does_not_report_a_subnet_or_new_devices():
    _seed_device(UNUSED_IP)

    summary = await run_ip_and_snmp_scan(ipscan=False)

    assert summary.subnet is None
    assert summary.devices_found == 0


@pytest.mark.asyncio
async def test_ipscan_false_leaves_unreachable_device_unidentified():
    device_id = _seed_device(UNUSED_IP)

    await run_ip_and_snmp_scan(ipscan=False)

    with db_connection_handler.get_session() as session:
        device = DeviceRepository(session).get_by_id(device_id)
        assert device.snmp_community is None


@pytest.fixture(scope="module")
def real_snmp_target():
    target = os.getenv("SNMP_TEST_TARGET")
    if not target:
        pytest.skip(
            "SNMP_TEST_TARGET não configurada — defina o IP de um device SNMP "
            "real para rodar o teste positivo de ipscan=False.",
            allow_module_level=True,
        )
    return target


@pytest.mark.asyncio
async def test_ipscan_false_identifies_existing_device_via_snmp(real_snmp_target):
    device_id = _seed_device(real_snmp_target)

    summary = await run_ip_and_snmp_scan(ipscan=False)

    assert summary.devices_probed >= 1
    assert summary.snmp_identified >= 1

    with db_connection_handler.get_session() as session:
        device = DeviceRepository(session).get_by_id(device_id)
        assert device.snmp_community is not None, (
            f"device real {real_snmp_target} não foi identificado via SNMP"
        )
