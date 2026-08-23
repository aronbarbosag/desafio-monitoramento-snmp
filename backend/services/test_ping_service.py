"""
Testes de integração REAIS do PingService.

Nada aqui é mockado: os pacotes ICMP saem de verdade pela rede (via scapy).
Os Device usados são instâncias soltas, nunca persistidas — o service não
toca no banco (mesma separação do MetricsCollectionService), então basta
setar os campos que ele lê (ip).
"""

import pytest

from models import Device

from .ping_service import PingService

# Faixa TEST-NET-2 (RFC 5737): reservada para documentação, nunca roteada.
UNUSED_IP = "198.51.100.3"
# Loopback: sempre alcançável, inclusive de dentro de um container Docker
# (é L3, ao contrário do ARP que precisa da LAN física) — dispensa depender
# de uma env var com IP real pra testar o caminho positivo.
LOOPBACK_IP = "127.0.0.1"


def _fake_device(device_id: int, ip: str) -> Device:
    return Device(id=device_id, ip=ip, mac="00:00:00:00:00:00")


@pytest.mark.asyncio
async def test_ping_unreachable_device_is_reported_offline():
    device = _fake_device(1, UNUSED_IP)

    results = await PingService().execute([device])

    assert len(results) == 1
    assert results[0].device_id == device.id
    assert results[0].online is False


@pytest.mark.asyncio
async def test_ping_reachable_device_is_reported_online():
    device = _fake_device(1, LOOPBACK_IP)

    results = await PingService().execute([device])

    assert len(results) == 1
    assert results[0].device_id == device.id
    assert results[0].online is True


@pytest.mark.asyncio
async def test_ping_multiple_devices_returns_one_result_each():
    devices = [_fake_device(1, LOOPBACK_IP), _fake_device(2, UNUSED_IP)]

    results = await PingService().execute(devices)

    results_by_id = {r.device_id: r for r in results}
    assert results_by_id[1].online is True
    assert results_by_id[2].online is False
