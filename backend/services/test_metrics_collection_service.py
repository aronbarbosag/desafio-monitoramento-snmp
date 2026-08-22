"""
Testes de integração REAIS do MetricsCollectionService.

Nada aqui é mockado: os pacotes SNMP saem de verdade pela rede. Os Device
usados são instâncias soltas, nunca persistidas — o service não toca no
banco (mesma separação do SnmpScanService), então basta setar os campos que
ele lê (ip, snmp_community).
"""

import os

import pytest

from models import Device
from snmp.oids import build_metric_definitions

from .metrics_collection_service import MetricsCollectionService

# Faixa TEST-NET-2 (RFC 5737): reservada para documentação, nunca roteada.
UNUSED_IP = "198.51.100.1"


def _fake_device(ip: str, community: str = "public") -> Device:
    return Device(id=1, ip=ip, mac="00:00:00:00:00:00", snmp_community=community)


@pytest.mark.asyncio
async def test_poll_unreachable_device_is_reported_offline():
    device = _fake_device(UNUSED_IP)
    metric_defs = build_metric_definitions()
    for i, metric_def in enumerate(metric_defs, start=1):
        metric_def.id = i

    results = await MetricsCollectionService().execute([device], metric_defs)

    assert len(results) == 1
    assert results[0].device_id == device.id
    assert results[0].online is False
    assert results[0].readings == []


@pytest.mark.asyncio
async def test_execute_with_no_metric_definitions_returns_empty():
    device = _fake_device(UNUSED_IP)

    results = await MetricsCollectionService().execute([device], [])

    assert results == []


@pytest.fixture(scope="module")
def real_snmp_target():
    target = os.getenv("SNMP_TEST_TARGET")
    if not target:
        pytest.skip(
            "SNMP_TEST_TARGET não configurada — defina o IP de um device SNMP "
            "real (ex: um snmpd local ou container Docker com snmpsimd) para "
            "rodar o teste positivo.",
            allow_module_level=True,
        )
    return target


@pytest.mark.asyncio
async def test_poll_real_device_returns_online_with_readings(real_snmp_target):
    device = _fake_device(real_snmp_target, community=os.getenv("SNMP_TEST_COMMUNITY", "public"))
    metric_defs = build_metric_definitions()
    for i, metric_def in enumerate(metric_defs, start=1):
        metric_def.id = i

    results = await MetricsCollectionService().execute([device], metric_defs)

    assert len(results) == 1
    result = results[0]
    assert result.online is True, f"device real {real_snmp_target} não respondeu ao poll"
    # sys_uptime (MIB-2 System) é o único OID do catálogo que praticamente todo
    # device SNMP suporta — hr_cpu_load (Host Resources MIB) pode faltar em
    # equipamentos "burros" como impressoras, e isso não é falha (ver
    # snmp/oids.py). Por isso validamos só que ALGUMA leitura veio.
    assert len(result.readings) >= 1
    sys_uptime_def = next(d for d in metric_defs if d.key == "sys_uptime")
    assert any(r.metric_definition_id == sys_uptime_def.id for r in result.readings)
