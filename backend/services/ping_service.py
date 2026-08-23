import asyncio
import logging
from dataclasses import dataclass

from scapy.all import ICMP, IP, sr1

from models import Device

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

DEFAULT_TIMEOUT_SECONDS = 2.0
DEFAULT_RETRIES = 1
MAX_CONCURRENT_PINGS = 20


@dataclass(frozen=True)
class PingResult:
    device_id: int
    online: bool


class PingService:
    """
    Sonda a disponibilidade (L3, via ICMP echo) de qualquer device, com ou
    sem SNMP — ao contrário do ARP do IpScanService (L2), atravessa a bridge
    do Docker normalmente, então funciona também dentro do container onde
    roda o ciclo de coleta em background.

    Não fala com o banco: devolve resultados puros, cabe ao composer decidir
    o que fazer (status, backoff, AvailabilityEvent) — mesma separação usada
    no MetricsCollectionService/SnmpScanService.
    """

    def __init__(self):
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_PINGS)

    def __send_ping(self, ip: str) -> bool:
        """Método síncrono (scapy é bloqueante): tenta até DEFAULT_RETRIES+1
        vezes, mesmo padrão de retry usado no ARP do IpScanService."""
        for _ in range(DEFAULT_RETRIES + 1):
            reply = sr1(IP(dst=ip) / ICMP(), timeout=DEFAULT_TIMEOUT_SECONDS, verbose=0)
            if reply is not None:
                return True
        return False

    async def __ping_device(self, device: Device) -> PingResult:
        async with self._semaphore:
            online = await asyncio.to_thread(self.__send_ping, device.ip)
        return PingResult(device_id=device.id, online=online)

    async def execute(self, devices: list[Device]) -> list[PingResult]:
        """Faz o ping de todos os devices em paralelo (limitado por
        MAX_CONCURRENT_PINGS) e devolve um resultado por device."""
        return list(await asyncio.gather(*(self.__ping_device(d) for d in devices)))
