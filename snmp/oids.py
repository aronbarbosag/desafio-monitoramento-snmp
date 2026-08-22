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
