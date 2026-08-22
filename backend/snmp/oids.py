from enum import StrEnum
from typing import NamedTuple

from models import MetricDefinition
from models.enums import MetricValueType


class SystemOID(StrEnum):
    """MIB-2 System group (RFC 1213) — identidade do device, não série temporal.
    Consultado uma vez pelo SnmpScanService, não pelo MetricsCollectionService."""

    SYS_DESCR = "1.3.6.1.2.1.1.1.0"
    SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
    SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
    SYS_NAME = "1.3.6.1.2.1.1.5.0"


class HostResourcesOID(StrEnum):
    """Host Resources MIB (RFC 2790). Nem todo device implementa — switches e
    equipamentos de rede "burros" tipicamente não respondem a essa MIB, então o
    MetricsCollectionService deve tratar "sem resposta nesse OID" como métrica
    não suportada, não como device offline."""

    HR_CPU_LOAD = "1.3.6.1.2.1.25.3.3.1.2.1"
    # hrPrinterDetectedErrorState do hrDeviceIndex 1 — índice fixo (mesma
    # simplificação do HR_CPU_LOAD acima). Confirmado por SNMP walk real
    # contra uma impressora Epson: hrDeviceIndex 1 é sempre a entrada do tipo
    # hrDevicePrinter quando o device SÓ tem uma impressora física.
    HR_PRINTER_DETECTED_ERROR_STATE = "1.3.6.1.2.1.25.3.5.1.2.1"


class PrinterOID(StrEnum):
    """Printer MIB (RFC 3805) — métricas específicas de impressora.

    prtMarkerSuppliesLevel é uma TABELA (um nível por suprimento — toner,
    cores de tinta etc.), não um escalar. O catálogo atual só suporta GET
    fixo (sem walk de tabela), então os 4 primeiros índices ficam
    hardcoded — cobre o caso real validado (impressora com 4 cartuchos de
    tinta: preto/ciano/magenta/amarelo). Em devices com menos suprimentos,
    os índices excedentes voltam NoSuchInstance e são descartados como
    métrica não suportada (mesmo tratamento do HR_CPU_LOAD em switches)."""

    MARKER_LIFE_COUNT = "1.3.6.1.2.1.43.10.2.1.4.1.1"
    MARKER_SUPPLIES_LEVEL_1 = "1.3.6.1.2.1.43.11.1.1.9.1.1"
    MARKER_SUPPLIES_LEVEL_2 = "1.3.6.1.2.1.43.11.1.1.9.1.2"
    MARKER_SUPPLIES_LEVEL_3 = "1.3.6.1.2.1.43.11.1.1.9.1.3"
    MARKER_SUPPLIES_LEVEL_4 = "1.3.6.1.2.1.43.11.1.1.9.1.4"


class MetricTemplate(NamedTuple):
    """Uma linha do catálogo de métricas — vira um MetricDefinition no banco."""

    key: str
    oid: str
    name: str
    value_type: MetricValueType
    unit: str | None = None


# O catálogo "universal" de métricas coletadas periodicamente (fase de polling,
# Step 4). Identidade do device (sysDescr/sysName/sysObjectID) não entra aqui —
# é consultada uma vez pelo SnmpScanService e vive direto nas colunas do Device.
METRIC_CATALOG: list[MetricTemplate] = [
    MetricTemplate(
        key="sys_uptime",
        oid=SystemOID.SYS_UPTIME,
        name="System Uptime",
        value_type=MetricValueType.COUNTER,
        unit="ticks",
    ),
    MetricTemplate(
        key="hr_cpu_load",
        oid=HostResourcesOID.HR_CPU_LOAD,
        name="CPU Load",
        value_type=MetricValueType.GAUGE,
        unit="%",
    ),
    MetricTemplate(
        key="printer_error_state",
        oid=HostResourcesOID.HR_PRINTER_DETECTED_ERROR_STATE,
        name="Printer Detected Error State",
        value_type=MetricValueType.STRING,
    ),
    MetricTemplate(
        key="printer_page_count",
        oid=PrinterOID.MARKER_LIFE_COUNT,
        name="Printer Marker Life Count",
        value_type=MetricValueType.COUNTER,
        unit="pages",
    ),
    MetricTemplate(
        key="printer_supply_level_1",
        oid=PrinterOID.MARKER_SUPPLIES_LEVEL_1,
        name="Marker Supply 1 Level",
        value_type=MetricValueType.INTEGER,
        unit="%",
    ),
    MetricTemplate(
        key="printer_supply_level_2",
        oid=PrinterOID.MARKER_SUPPLIES_LEVEL_2,
        name="Marker Supply 2 Level",
        value_type=MetricValueType.INTEGER,
        unit="%",
    ),
    MetricTemplate(
        key="printer_supply_level_3",
        oid=PrinterOID.MARKER_SUPPLIES_LEVEL_3,
        name="Marker Supply 3 Level",
        value_type=MetricValueType.INTEGER,
        unit="%",
    ),
    MetricTemplate(
        key="printer_supply_level_4",
        oid=PrinterOID.MARKER_SUPPLIES_LEVEL_4,
        name="Marker Supply 4 Level",
        value_type=MetricValueType.INTEGER,
        unit="%",
    ),
]


def build_metric_definitions() -> list[MetricDefinition]:
    """Materializa o catálogo acima em instâncias ORM novas, prontas pra upsert."""
    return [
        MetricDefinition(
            key=template.key,
            oid=template.oid,
            name=template.name,
            value_type=template.value_type,
            unit=template.unit,
        )
        for template in METRIC_CATALOG
    ]
