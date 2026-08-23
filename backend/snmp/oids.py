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
    SYS_CONTACT = "1.3.6.1.2.1.1.4.0"
    SYS_NAME = "1.3.6.1.2.1.1.5.0"
    SYS_LOCATION = "1.3.6.1.2.1.1.6.0"


class HostResourcesTableOID(StrEnum):
    """Host Resources MIB (RFC 2790) — bases de COLUNA de tabela. Quantidade
    de CPUs e de unidades de armazenamento varia por device (mesmo problema
    do PrinterMibOID), então não entram no METRIC_CATALOG estático — são
    resolvidos via walk dinâmico em
    services/host_resources_metrics_service.py."""

    HR_PROCESSOR_LOAD_COL = "1.3.6.1.2.1.25.3.3.1.2"
    HR_STORAGE_DESCR_COL = "1.3.6.1.2.1.25.2.3.1.3"
    HR_STORAGE_ALLOCATION_UNITS_COL = "1.3.6.1.2.1.25.2.3.1.4"
    HR_STORAGE_SIZE_COL = "1.3.6.1.2.1.25.2.3.1.5"
    HR_STORAGE_USED_COL = "1.3.6.1.2.1.25.2.3.1.6"


class IfMibOID(StrEnum):
    """IF-MIB (RFC 2863) — interfaces de rede. Quantidade de interfaces varia
    por device (1 numa impressora, dezenas num switch) — mesma lógica de
    walk dinâmico, ver services/host_resources_metrics_service.py."""

    IF_DESCR_COL = "1.3.6.1.2.1.2.2.1.2"
    IF_OPER_STATUS_COL = "1.3.6.1.2.1.2.2.1.8"
    IF_IN_OCTETS_COL = "1.3.6.1.2.1.2.2.1.10"
    IF_IN_ERRORS_COL = "1.3.6.1.2.1.2.2.1.14"
    IF_OUT_OCTETS_COL = "1.3.6.1.2.1.2.2.1.16"
    IF_OUT_ERRORS_COL = "1.3.6.1.2.1.2.2.1.20"


class PrinterMibOID(StrEnum):
    """Printer MIB (RFC 3805) / hrPrinterTable — bases de COLUNA de tabela, não
    escalares prontos pra GET. O hrDeviceIndex da impressora e a quantidade/
    ordem dos suprimentos variam por device (confirmado: nesta LAN é índice 1
    com 4 cartuchos de tinta, mas isso não generaliza pra outras redes/
    fabricantes). Por isso não entram no METRIC_CATALOG estático — são
    resolvidos via walk dinâmico (snmp/snmp_walk.py.walk_column) em
    services/snmp_scan_service.py (identidade) e
    services/printer_metrics_service.py (métricas), um walk por ciclo em vez
    de um índice cacheado."""

    PRT_GENERAL_PRINTER_NAME_COL = "1.3.6.1.2.1.43.5.1.1.16"
    HR_PRINTER_DETECTED_ERROR_STATE_COL = "1.3.6.1.2.1.25.3.5.1.2"
    PRT_MARKER_LIFE_COUNT_COL = "1.3.6.1.2.1.43.10.2.1.4"
    PRT_MARKER_SUPPLIES_DESCRIPTION_COL = "1.3.6.1.2.1.43.11.1.1.6"
    PRT_MARKER_SUPPLIES_LEVEL_COL = "1.3.6.1.2.1.43.11.1.1.9"


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
