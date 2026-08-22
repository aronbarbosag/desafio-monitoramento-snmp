"""
Testes de integração REAIS do IpScanService.

Nada aqui é mockado: os pacotes ARP saem de verdade pela placa de rede e as
asserções são feitas em cima das respostas dos dispositivos que estão ligados
na sua LAN neste momento.

Requisitos para rodar:
  * Npcap instalado (https://npcap.com) — sem ele o scapy não abre a camada 2;
  * terminal com privilégio de Administrador (a menos que o Npcap tenha sido
    instalado sem a opção "Restrict Npcap driver's access to Administrators").

Se algum requisito faltar, os testes são pulados com a mensagem do motivo.
"""

import asyncio
import ipaddress
import re

import pytest
from scapy.all import conf

from .ip_scan_service import IpScanService, detect_local_subnet

MAC_REGEX = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$", re.IGNORECASE)

# Faixa TEST-NET-2 (RFC 5737): reservada para documentação, nunca roteada.
# Nenhuma máquina real pode responder ARP nela.
UNUSED_SUBNET = "198.51.100.0/30"


def _layer2_reason():
    """Retorna o motivo de não conseguir usar camada 2, ou None se estiver OK."""
    socket_cls = conf.L2socket
    if socket_cls is None or "NotAvailable" in socket_cls.__name__:
        return (
            "camada 2 indisponível para o scapy "
            f"({getattr(socket_cls, '__name__', socket_cls)}). "
            "Instale o Npcap e rode o pytest como Administrador."
        )
    return None


def _default_route():
    """(iface, ip_local, gateway) da rota default real da máquina."""
    return conf.route.route("0.0.0.0")


@pytest.fixture(scope="module")
def real_network():
    """Pula o módulo inteiro se a máquina não puder fazer um scan de verdade."""
    reason = _layer2_reason()
    if reason:
        pytest.skip(reason, allow_module_level=True)

    subnet = detect_local_subnet()
    _, _local_ip, gateway = _default_route()
    return {"subnet": subnet, "gateway": gateway}


@pytest.fixture(scope="module")
def scan_result(real_network):
    """Executa UM scan real e reaproveita o resultado nos testes do módulo."""
    scanner = IpScanService(ip_subnet=real_network["subnet"])
    devices = asyncio.run(scanner.execute())

    print(f"\nDispositivos encontrados em {real_network['subnet']}: {len(devices)}")
    for device in devices:
        vendor = device["vendor"] or "desconhecido"
        print(f"  - {device['ip']:<15} {device['mac']}  {vendor}")

    return devices


def test_scan_finds_at_least_one_real_device(scan_result, real_network):
    assert scan_result, (
        f"nenhum dispositivo respondeu ARP em {real_network['subnet']}. "
        "Verifique se o cabo/Wi-Fi está ativo e se o firewall não está "
        "bloqueando o envio dos pacotes."
    )


def test_every_device_has_valid_ip_and_mac(scan_result):
    for device in scan_result:
        assert set(device) == {"ip", "mac", "vendor"}, f"chaves inesperadas em {device}"
        # Levanta ValueError se não for um IPv4 válido.
        ipaddress.ip_address(device["ip"])
        assert MAC_REGEX.match(device["mac"]), f"MAC inválido: {device['mac']}"
        assert device["vendor"] is None or isinstance(device["vendor"], str)


def test_every_device_belongs_to_the_scanned_subnet(scan_result, real_network):
    network = ipaddress.ip_network(real_network["subnet"], strict=False)
    for device in scan_result:
        assert ipaddress.ip_address(device["ip"]) in network, (
            f"{device['ip']} está fora de {network}"
        )


def test_scan_does_not_return_duplicated_ips(scan_result):
    ips = [device["ip"] for device in scan_result]
    assert len(ips) == len(set(ips)), f"IPs duplicados no resultado: {ips}"


def test_default_gateway_answers_the_scan(scan_result, real_network):
    gateway = real_network["gateway"]
    found = {device["ip"] for device in scan_result}
    assert gateway in found, (
        f"o gateway {gateway} não apareceu no scan. Encontrados: {sorted(found)}"
    )


def test_at_least_one_device_has_a_known_vendor(scan_result):
    vendors = [device["vendor"] for device in scan_result if device["vendor"]]
    assert vendors, "nenhum MAC do scan bateu com a base de fabricantes (OUI) do scapy"


@pytest.mark.asyncio
async def test_scan_on_unused_subnet_returns_empty_list(real_network):
    scanner = IpScanService(ip_subnet=UNUSED_SUBNET)

    devices = await scanner.execute()

    assert devices == [], f"alguém respondeu ARP na faixa reservada {UNUSED_SUBNET}: {devices}"


@pytest.mark.asyncio
async def test_scan_without_subnet_autodetects_the_local_network(real_network):
    """Sem informar ip_subnet, o serviço detecta e escaneia a rede local sozinho."""
    scanner = IpScanService()

    assert scanner.subnet == real_network["subnet"]

    devices = await scanner.execute()

    assert devices, "o auto-detect não encontrou a rede local real"
