import asyncio
from dataclasses import dataclass

from pysnmp.hlapi.v3arch.asyncio import SnmpEngine

from models import Device
from models.enums import MetricValueType
from services.dynamic_metric_reading import DynamicMetricReading, keyed_readings, slugify
from snmp.oids import HostResourcesTableOID, IfMibOID
from snmp.snmp_walk import walk_column

DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_RETRIES = 1
MAX_CONCURRENT_POLLS = 20


@dataclass(frozen=True)
class HostResourcesPollResult:
    device_id: int
    readings: list[DynamicMetricReading]


def _safe_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


class HostResourcesMetricsService:
    """Coleta dinâmica de Host Resources MIB (RFC 2790, CPU/armazenamento) e
    IF-MIB (RFC 2863, interfaces de rede).

    Mesma razão de ser do PrinterMetricsService (walk fresco a cada ciclo em
    vez de índice cacheado, ver snmp/snmp_walk.py), mas roda pra QUALQUER
    device SNMP-capable, não só impressora: quantidade de CPUs, discos e
    interfaces varia por device do mesmo jeito que a quantidade de
    suprimentos varia por impressora.
    """

    def __init__(self):
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_POLLS)

    async def __poll_device(self, engine: SnmpEngine, device: Device) -> HostResourcesPollResult:
        async with self._semaphore:
            (
                cpu_load,
                storage_descr,
                storage_units,
                storage_size,
                storage_used,
                if_descr,
                if_status,
                if_in_octets,
                if_out_octets,
                if_in_errors,
                if_out_errors,
            ) = await asyncio.gather(
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    HostResourcesTableOID.HR_PROCESSOR_LOAD_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    HostResourcesTableOID.HR_STORAGE_DESCR_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    HostResourcesTableOID.HR_STORAGE_ALLOCATION_UNITS_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    HostResourcesTableOID.HR_STORAGE_SIZE_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    HostResourcesTableOID.HR_STORAGE_USED_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    IfMibOID.IF_DESCR_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    IfMibOID.IF_OPER_STATUS_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    IfMibOID.IF_IN_OCTETS_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    IfMibOID.IF_OUT_OCTETS_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    IfMibOID.IF_IN_ERRORS_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
                walk_column(
                    engine,
                    device.ip,
                    device.snmp_community,
                    IfMibOID.IF_OUT_ERRORS_COL,
                    DEFAULT_TIMEOUT_SECONDS,
                    DEFAULT_RETRIES,
                ),
            )

        readings: list[DynamicMetricReading] = [
            *keyed_readings(cpu_load, "hr_cpu_load", "CPU Load", MetricValueType.GAUGE, "%"),
        ]

        for index, size_raw in storage_size.items():
            used_raw = storage_used.get(index)
            unit_bytes = _safe_int(storage_units.get(index))
            size_units = _safe_int(size_raw)
            used_units = _safe_int(used_raw)
            if unit_bytes is None or size_units is None:
                continue
            label = storage_descr.get(index) or f"Storage {index}"
            key_base = f"storage_{slugify(label)}"
            readings.append(
                DynamicMetricReading(
                    f"{key_base}_total_bytes",
                    f"{label} Total",
                    MetricValueType.GAUGE,
                    str(size_units * unit_bytes),
                    "bytes",
                )
            )
            if used_units is not None:
                readings.append(
                    DynamicMetricReading(
                        f"{key_base}_used_bytes",
                        f"{label} Used",
                        MetricValueType.GAUGE,
                        str(used_units * unit_bytes),
                        "bytes",
                    )
                )
                if size_units > 0:
                    percent = round(used_units / size_units * 100, 1)
                    readings.append(
                        DynamicMetricReading(
                            f"{key_base}_used_percent",
                            f"{label} Used %",
                            MetricValueType.GAUGE,
                            str(percent),
                            "%",
                        )
                    )

        for index, descr in if_descr.items():
            label = descr or f"Interface {index}"
            key_base = f"if_{slugify(label)}"
            if (status := if_status.get(index)) is not None:
                readings.append(
                    DynamicMetricReading(
                        f"{key_base}_status", f"{label} Status", MetricValueType.INTEGER, status
                    )
                )
            if (in_octets := if_in_octets.get(index)) is not None:
                readings.append(
                    DynamicMetricReading(
                        f"{key_base}_in_octets",
                        f"{label} In",
                        MetricValueType.COUNTER,
                        in_octets,
                        "bytes",
                    )
                )
            if (out_octets := if_out_octets.get(index)) is not None:
                readings.append(
                    DynamicMetricReading(
                        f"{key_base}_out_octets",
                        f"{label} Out",
                        MetricValueType.COUNTER,
                        out_octets,
                        "bytes",
                    )
                )
            if (in_errors := if_in_errors.get(index)) is not None:
                readings.append(
                    DynamicMetricReading(
                        f"{key_base}_in_errors",
                        f"{label} In Errors",
                        MetricValueType.COUNTER,
                        in_errors,
                        "errors",
                    )
                )
            if (out_errors := if_out_errors.get(index)) is not None:
                readings.append(
                    DynamicMetricReading(
                        f"{key_base}_out_errors",
                        f"{label} Out Errors",
                        MetricValueType.COUNTER,
                        out_errors,
                        "errors",
                    )
                )

        return HostResourcesPollResult(device_id=device.id, readings=readings)

    async def execute(self, devices: list[Device]) -> list[HostResourcesPollResult]:
        if not devices:
            return []
        engine = SnmpEngine()
        return list(await asyncio.gather(*(self.__poll_device(engine, d) for d in devices)))
