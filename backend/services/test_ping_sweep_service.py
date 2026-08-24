"""
Testes de integração REAIS do PingSweepService — pacotes ICMP saem de
verdade pela rede, via subprocess do `ping` do SO (ver
services/ping_sweep_service.py). Ao contrário do IpScanService (ARP/L2), não
depende de Npcap/Administrador nem de socket raw — mesmo motivo pelo qual
test_ping_service.py não tem skip condicional.
"""

import pytest
from scapy.all import conf

from .ip_scan_service import detect_local_subnet
from .ping_sweep_service import PingSweepService

# Faixa TEST-NET-2 (RFC 5737): reservada para documentação, nunca roteada.
UNUSED_SUBNET = "198.51.100.0/30"


@pytest.mark.asyncio
async def test_sweep_on_unused_subnet_finds_nothing():
    results = await PingSweepService(UNUSED_SUBNET).execute()

    assert results, "a subnet /30 devia ter pelo menos os 2 hosts endereçáveis"
    assert all(not r.online for r in results), (
        f"alguém respondeu ICMP na faixa reservada {UNUSED_SUBNET}: {results}"
    )


@pytest.mark.asyncio
async def test_sweep_finds_the_default_gateway():
    subnet = detect_local_subnet()
    _iface, _local_ip, gateway = conf.route.route("0.0.0.0")

    results = await PingSweepService(subnet).execute()

    online_ips = {r.ip for r in results if r.online}
    assert gateway in online_ips, (
        f"o gateway {gateway} não respondeu ao ping sweep em {subnet}. "
        "Verifique se o firewall não está bloqueando ICMP de saída."
    )
