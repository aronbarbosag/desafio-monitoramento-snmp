"""
Testes de integração REAIS do SnmpScanService.

Nada aqui é mockado: os pacotes SNMP saem de verdade pela rede. O teste
negativo (endereço reservado, nunca responde) roda sempre. O teste positivo
depende de um device SNMP de verdade acessível — como a maioria das LANs
domésticas/office não tem um, ele é pulado a menos que SNMP_TEST_TARGET esteja
configurada (ex: um snmpd real ou um container Docker com snmpsimd).
"""

import os
import time

import pytest

from .snmp_scan_service import SnmpScanService

# Faixa TEST-NET-2 (RFC 5737): reservada para documentação, nunca roteada.
# Nenhum device real pode responder SNMP nela.
UNUSED_IP = "198.51.100.1"


@pytest.mark.asyncio
async def test_scan_on_unused_ip_returns_empty_list():
    scanner = SnmpScanService()

    t0 = time.monotonic()
    results = await scanner.execute([UNUSED_IP])
    elapsed = time.monotonic() - t0

    assert results == [], f"algo respondeu SNMP em {UNUSED_IP}: {results}"
    # Confirma que é um timeout curto e definitivo, não um retry sem fim.
    assert elapsed < 10, f"scan de 1 IP sem resposta demorou {elapsed:.1f}s"


@pytest.mark.asyncio
async def test_scan_runs_multiple_ips_concurrently():
    scanner = SnmpScanService()
    ips = [f"198.51.100.{i}" for i in range(1, 6)]

    t0 = time.monotonic()
    results = await scanner.execute(ips)
    elapsed = time.monotonic() - t0

    assert results == []
    # Se rodasse sequencial, 5 IPs x ~3s de timeout/retry dariam ~15s.
    assert elapsed < 8, f"5 IPs sem resposta demoraram {elapsed:.1f}s — não parece paralelo"


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
async def test_scan_finds_a_real_snmp_device(real_snmp_target):
    scanner = SnmpScanService(community=os.getenv("SNMP_TEST_COMMUNITY", "public"))

    results = await scanner.execute([real_snmp_target])

    assert len(results) == 1, f"nenhuma resposta SNMP de {real_snmp_target}"
    result = results[0]
    assert result.ip == real_snmp_target
    assert result.sys_descr
    assert result.sys_object_id
