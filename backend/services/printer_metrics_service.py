import asyncio
from dataclasses import dataclass

from pysnmp.hlapi.v3arch.asyncio import SnmpEngine

from models import Device
from models.enums import MetricValueType
from services.dynamic_metric_reading import DynamicMetricReading, keyed_readings, slugify
from snmp.oids import PrinterMibOID
from snmp.snmp_walk import walk_column

DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_RETRIES = 1
MAX_CONCURRENT_POLLS = 20


@dataclass(frozen=True)
class PrinterPollResult:
    device_id: int
    readings: list[DynamicMetricReading]


class PrinterMetricsService:
    """Coleta dinâmica de métricas de impressora (Printer MIB, RFC 3805).

    Ao contrário do MetricsCollectionService (catálogo estático, GET em bloco
    com OID fixo), aqui o hrDeviceIndex da impressora e a quantidade/ordem dos
    suprimentos variam por device — então cada ciclo faz um walk fresco (ver
    snmp/snmp_walk.py) em vez de reusar um índice cacheado de scan anterior.
    Só roda pros devices já identificados como impressora (Device.model_name
    setado pelo SnmpScanService); o custo extra de rede por walk é aceitável
    porque o intervalo mínimo de poll já é 60s (services/polling_backoff.py).
    """

    def __init__(self):
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_POLLS)

    async def __poll_device(self, engine: SnmpEngine, device: Device) -> PrinterPollResult:
        async with self._semaphore:
            error_state, life_count, description, level = await asyncio.gather(
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    PrinterMibOID.HR_PRINTER_DETECTED_ERROR_STATE_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    PrinterMibOID.PRT_MARKER_LIFE_COUNT_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    PrinterMibOID.PRT_MARKER_SUPPLIES_DESCRIPTION_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    PrinterMibOID.PRT_MARKER_SUPPLIES_LEVEL_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
            )

        readings = [
            *keyed_readings(
                error_state,
                "printer_error_state",
                "Printer Detected Error State",
                MetricValueType.STRING,
            ),
            *keyed_readings(
                life_count,
                "printer_page_count",
                "Printer Marker Life Count",
                MetricValueType.COUNTER,
                "pages",
            ),
        ]
        for index, level_value in level.items():
            description_text = description.get(index)
            if description_text:
                key = f"printer_supply_{slugify(description_text)}_level"
                name = f"{description_text} Level"
            else:
                key = f"printer_supply_{index.replace('.', '_')}_level"
                name = f"Marker Supply {index} Level"
            readings.append(
                DynamicMetricReading(key, name, MetricValueType.INTEGER, level_value, "%")
            )

        return PrinterPollResult(device_id=device.id, readings=readings)

    async def execute(self, devices: list[Device]) -> list[PrinterPollResult]:
        """Sonda só os devices com model_name setado (identificados como
        impressora pelo SnmpScanService); os demais não custam nada aqui."""
        printers = [d for d in devices if d.model_name]
        if not printers:
            return []
        engine = SnmpEngine()
        return list(await asyncio.gather(*(self.__poll_device(engine, d) for d in printers)))
