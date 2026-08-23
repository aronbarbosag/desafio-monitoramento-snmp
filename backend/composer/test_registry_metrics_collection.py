"""
Testes de integração REAIS de run_collection_cycle() — sem mocks, os pacotes
ICMP saem de verdade pela rede (via PingService). Foco aqui é o novo
comportamento: devices sem SNMP também ganham status ONLINE/OFFLINE via
ping, em vez de ficar travados em UNKNOWN por nunca entrar no ciclo.
"""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import pytest

from infra.database.db_connection_handler import db_connection_handler
from models import Device, DeviceStatus, MetricValueType, Subnet
from repositories.device_repository import DeviceRepository
from repositories.metric_definition_repository import MetricDefinitionRepository
from repositories.subnet_repository import SubnetRepository

from . import registry_metrics_collection as rmc
from .registry_metrics_collection import run_collection_cycle

# Faixa TEST-NET-2 (RFC 5737): reservada para documentação, nunca roteada.
UNUSED_IP = "198.51.100.4"
# Loopback: sempre alcançável, mesmo sem depender de outro host na rede.
LOOPBACK_IP = "127.0.0.1"


def _seed_device(session, ip: str) -> int:
    subnet = SubnetRepository(session).save(Subnet(cidr="0.0.0.0/32"))
    past = datetime.now(UTC) - timedelta(minutes=1)
    device = DeviceRepository(session).save_many(
        [Device(ip=ip, mac="00:00:00:00:00:00", subnet_id=subnet.id, next_poll_at=past)]
    )[0]
    return device.id


@pytest.mark.asyncio
async def test_collection_cycle_marks_reachable_snmp_less_device_online():
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session, LOOPBACK_IP)

    await run_collection_cycle()

    with db_connection_handler.get_session() as session:
        device = DeviceRepository(session).get_by_id(device_id)
        assert device.status == DeviceStatus.ONLINE


@pytest.mark.asyncio
async def test_collection_cycle_marks_unreachable_snmp_less_device_offline():
    with db_connection_handler.get_session() as session:
        device_id = _seed_device(session, UNUSED_IP)

    await run_collection_cycle()

    with db_connection_handler.get_session() as session:
        device = DeviceRepository(session).get_by_id(device_id)
        assert device.status == DeviceStatus.OFFLINE


@pytest.mark.asyncio
async def test_collection_cycle_does_not_crash_with_a_dynamic_metric_in_the_catalog():
    """Regressão: um MetricDefinition com oid="dynamic" (criado em runtime por
    um walk anterior, ex: PrinterMetricsService) não pode quebrar o GET SNMP
    estático — se quebrar, a sessão inteira do ciclo dá rollback e a task de
    run_forever() morre silenciosamente pra sempre."""
    with db_connection_handler.get_session() as session:
        subnet = SubnetRepository(session).save(Subnet(cidr="0.0.0.0/32"))
        past = datetime.now(UTC) - timedelta(minutes=1)
        device_id = (
            DeviceRepository(session)
            .save_many(
                [
                    Device(
                        ip=LOOPBACK_IP,
                        mac="00:00:00:00:00:00",
                        subnet_id=subnet.id,
                        next_poll_at=past,
                        snmp_supported=True,
                        snmp_community="public",
                    )
                ]
            )[0]
            .id
        )
        MetricDefinitionRepository(session).get_or_create(
            "if_octets_eth0", name="eth0 octets", value_type=MetricValueType.GAUGE
        )

    await run_collection_cycle()

    with db_connection_handler.get_session() as session:
        device = DeviceRepository(session).get_by_id(device_id)
        assert device.status == DeviceStatus.ONLINE


@pytest.mark.asyncio
async def test_run_forever_keeps_looping_after_a_cycle_raises(monkeypatch):
    """Regressão: um ciclo que estoura exceção (ex: o bug acima, ou qualquer
    outro) não pode matar a task de run_forever() pra sempre — sem isso, uma
    falha isolada trava o status de todo mundo em UNKNOWN até reiniciar a
    aplicação."""
    call_count = 0

    async def flaky_cycle() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("ciclo falhou de propósito, pra testar a resiliência")

    monkeypatch.setattr(rmc, "run_collection_cycle", flaky_cycle)
    monkeypatch.setattr(rmc, "TICK_INTERVAL_SECONDS", 0)

    task = asyncio.create_task(rmc.run_forever())
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
