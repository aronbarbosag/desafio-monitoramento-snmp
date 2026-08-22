import asyncio
from dataclasses import dataclass

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
)

from snmp.oids import SystemOID

SNMP_PORT = 161
DEFAULT_COMMUNITY = "public"
# Timeout curto e pouca retry de propósito: aqui só queremos saber "esse IP fala
# SNMP ou não". Isso é diferente do backoff do MetricsCollectionService (Step 4),
# que cresce a cada falha — aqui cada tentativa já é rápida e definitiva.
DEFAULT_TIMEOUT_SECONDS = 1.5
DEFAULT_RETRIES = 1
MAX_CONCURRENT_PROBES = 20


@dataclass(frozen=True)
class SnmpScanResult:
    ip: str
    sys_descr: str
    sys_name: str
    sys_object_id: str
    community: str


class SnmpScanService:
    """
    Recebe uma lista de IPs (tipicamente a saída do IpScanService) e tenta um
    SNMP GET no grupo System (sysDescr/sysName/sysObjectID) de cada um.

    Quem responde é SNMP-capable e entra no resultado; quem não responde
    (timeout) simplesmente não entra — não é um erro, é o esperado pra maioria
    dos hosts numa LAN doméstica/office.
    """

    def __init__(self, community: str = DEFAULT_COMMUNITY):
        self.community = community
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_PROBES)

    async def __probe(self, engine: SnmpEngine, ip: str) -> SnmpScanResult | None:
        async with self._semaphore:
            transport = await UdpTransportTarget.create(
                (ip, SNMP_PORT),
                timeout=DEFAULT_TIMEOUT_SECONDS,
                retries=DEFAULT_RETRIES,
            )
            error_indication, error_status, _error_index, var_binds = await get_cmd(
                engine,
                CommunityData(self.community),
                transport,
                ContextData(),
                ObjectType(ObjectIdentity(SystemOID.SYS_DESCR)),
                ObjectType(ObjectIdentity(SystemOID.SYS_NAME)),
                ObjectType(ObjectIdentity(SystemOID.SYS_OBJECT_ID)),
            )

        if error_indication or error_status:
            return None

        sys_descr, sys_name, sys_object_id = (str(value) for _oid, value in var_binds)
        return SnmpScanResult(
            ip=ip,
            sys_descr=sys_descr,
            sys_name=sys_name,
            sys_object_id=sys_object_id,
            community=self.community,
        )

    async def execute(self, ips: list[str]) -> list[SnmpScanResult]:
        """Varre todos os IPs em paralelo (limitado por MAX_CONCURRENT_PROBES) e
        devolve só quem respondeu."""
        engine = SnmpEngine()
        results = await asyncio.gather(*(self.__probe(engine, ip) for ip in ips))
        return [result for result in results if result is not None]
