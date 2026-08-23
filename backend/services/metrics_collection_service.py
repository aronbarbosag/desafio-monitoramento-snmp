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
from pysnmp.proto.rfc1905 import NoSuchInstance, NoSuchObject

from models import Device, MetricDefinition

SNMP_PORT = 161
# Timeout maior e com retry (ao contrário do SnmpScanService): aqui o device já é
# SNMP-capable e conhecido, então vale a pena insistir um pouco antes de marcar a
# falha que vai disparar o backoff.
DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_RETRIES = 1
MAX_CONCURRENT_POLLS = 20

_UNSUPPORTED_VALUE_TYPES = (NoSuchObject, NoSuchInstance)


@dataclass(frozen=True)
class MetricReading:
    metric_definition_id: int
    raw_value: str


@dataclass(frozen=True)
class DevicePollResult:
    device_id: int
    readings: list[MetricReading]


class MetricsCollectionService:
    """
    Recebe devices já conhecidos como SNMP-capable (snmp_supported=True) e o
    catálogo de métricas, faz um GET em bloco (todos os OIDs do catálogo numa
    única PDU) por device — só pra coletar métricas. Quem decide disponibilidade
    (status/backoff) é o PingService; um GET que falhar aqui só significa "sem
    métricas nesse ciclo", nunca marca o device como offline.

    Não fala com o banco: devolve resultados puros, cabe ao composer decidir o
    que fazer com as leituras (MetricHistory) — mesma separação usada no
    SnmpScanService.

    Um OID não suportado pelo device (ex: Host Resources MIB numa impressora)
    aparece como NoSuchObject/NoSuchInstance só naquele var-bind — a métrica é
    descartada da leitura. A ausência de resposta na PDU inteira (timeout,
    community errada) simplesmente resulta em readings vazio.
    """

    def __init__(self):
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_POLLS)

    async def __poll_device(
        self,
        engine: SnmpEngine,
        device: Device,
        metric_defs: list[MetricDefinition],
    ) -> DevicePollResult:
        async with self._semaphore:
            transport = await UdpTransportTarget.create(
                (device.ip, SNMP_PORT),
                timeout=DEFAULT_TIMEOUT_SECONDS,
                retries=DEFAULT_RETRIES,
            )
            error_indication, error_status, _error_index, var_binds = await get_cmd(
                engine,
                CommunityData(device.snmp_community),
                transport,
                ContextData(),
                *(ObjectType(ObjectIdentity(metric_def.oid)) for metric_def in metric_defs),
            )

        if error_indication or error_status:
            return DevicePollResult(device_id=device.id, readings=[])

        readings = [
            MetricReading(metric_definition_id=metric_def.id, raw_value=str(value))
            for metric_def, (_oid, value) in zip(metric_defs, var_binds, strict=True)
            if not isinstance(value, _UNSUPPORTED_VALUE_TYPES)
        ]
        return DevicePollResult(device_id=device.id, readings=readings)

    async def execute(
        self,
        devices: list[Device],
        metric_defs: list[MetricDefinition],
    ) -> list[DevicePollResult]:
        """Faz o polling de todos os devices em paralelo (limitado por
        MAX_CONCURRENT_POLLS) e devolve um resultado por device."""
        if not metric_defs:
            return []
        engine = SnmpEngine()
        return list(
            await asyncio.gather(*(self.__poll_device(engine, d, metric_defs) for d in devices))
        )
