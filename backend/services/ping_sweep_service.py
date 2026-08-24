import asyncio
import ipaddress
import platform
from dataclasses import dataclass

from .ip_scan_service import MAX_SCAN_HOSTS, SubnetTooLargeError

# scapy manda ICMP via socket raw (IP()/ICMP() + sr()): pra cada IP sem
# entrada na ARP cache — a imensa maioria numa varredura de subnet — ele
# precisa resolver o MAC do próximo salto antes do envio, em vez de
# multiplexar tudo numa única chamada como no ARP (que não depende dessa
# resolução prévia). Medido tanto no Windows/Npcap quanto dentro de um
# container Docker: ~1-2s por host nessas condições, o que não termina em
# tempo hábil numa /24 inteira (254 hosts). O `ping` nativo do SO usa a
# pilha ICMP do kernel diretamente e não tem esse gargalo — por isso é usado
# sempre, independente de plataforma.
WINDOWS_PING_TIMEOUT_MS = 800
UNIX_PING_TIMEOUT_SECONDS = 1
MAX_CONCURRENT_PINGS = 100


@dataclass(frozen=True)
class PingSweepResult:
    ip: str
    online: bool


def _ping_command(ip: str) -> list[str]:
    if platform.system() == "Windows":
        return ["ping", "-n", "1", "-w", str(WINDOWS_PING_TIMEOUT_MS), ip]
    return ["ping", "-c", "1", "-W", str(UNIX_PING_TIMEOUT_SECONDS), ip]


class PingSweepService:
    """Varre uma subnet inteira via ICMP echo (L3, usando o `ping` do SO) —
    ao contrário do ARP do IpScanService (L2), atravessa a bridge do Docker
    normalmente, então funciona também de dentro do container onde o ARP não
    tem acesso à LAN física (ver backend/README.md e Dockerfile, que instala
    o pacote `ping` na imagem).

    Não identifica MAC/fabricante (ICMP não carrega isso). Usado sozinho
    (via GET /network/ping-sweep) é só diagnóstico: "quem está de pé nessa
    subnet agora". registry_devices.run_ip_and_snmp_scan também usa como
    fallback quando o ARP não acha nada — nesse caso os IPs achados aqui
    viram Device com mac=None (ver Device.mac, nullable, e
    DeviceRepository.upsert_many)."""

    def __init__(self, subnet: str):
        network = ipaddress.ip_network(subnet, strict=False)
        if network.num_addresses > MAX_SCAN_HOSTS:
            raise SubnetTooLargeError(subnet, network.num_addresses)
        self._hosts = [str(ip) for ip in network.hosts()]

    async def __ping(self, ip: str, semaphore: asyncio.Semaphore) -> PingSweepResult:
        async with semaphore:
            proc = await asyncio.create_subprocess_exec(
                *_ping_command(ip),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            returncode = await proc.wait()
        return PingSweepResult(ip=ip, online=returncode == 0)

    async def execute(self) -> list[PingSweepResult]:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PINGS)
        return list(await asyncio.gather(*(self.__ping(ip, semaphore) for ip in self._hosts)))
