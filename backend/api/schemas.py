from datetime import datetime

from pydantic import BaseModel, ConfigDict

from etl.metric_formatting import humanize_metric_display
from models import DeviceStatus, MetricHistory, MetricValueType


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip: str
    mac: str | None
    vendor: str | None
    device_type: str | None
    hostname: str | None
    sys_descr: str | None
    model_name: str | None
    sys_contact: str | None
    sys_location: str | None
    snmp_supported: bool
    status: DeviceStatus
    poll_interval_seconds: int
    consecutive_failures: int
    last_checked_at: datetime | None


class MetricHistoryOut(BaseModel):
    id: int
    collected_at: datetime
    metric_key: str
    metric_name: str
    metric_unit: str | None
    value_type: MetricValueType
    value_numeric: float | None
    value_text: str | None
    display_value: str | None

    @classmethod
    def from_model(cls, history: MetricHistory) -> "MetricHistoryOut":
        return cls(
            id=history.id,
            collected_at=history.collected_at,
            metric_key=history.metric_definition.key,
            metric_name=history.metric_definition.name,
            metric_unit=history.metric_definition.unit,
            value_type=history.metric_definition.value_type,
            value_numeric=history.value_numeric,
            value_text=history.value_text,
            display_value=humanize_metric_display(
                history.metric_definition.unit, history.value_numeric
            ),
        )


class AvailabilityEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: DeviceStatus
    started_at: datetime
    ended_at: datetime | None


class ScanResult(BaseModel):
    subnet: str | None
    devices_found: int
    devices_probed: int
    snmp_identified: int
    # True quando o ARP não achou nada (sem acesso L2 à LAN física — o caso
    # comum de dentro do Docker) e o scan caiu pro PingSweepService (ICMP):
    # devices_found nesse caso não tem MAC/fabricante, só IP.
    used_ping_sweep_fallback: bool = False


class ChartPoint(BaseModel):
    """Ponto pronto pra plotar — formato agnóstico de lib de gráfico: o
    frontend que mapeia isso pro `option` do ECharts (ou outra), o backend
    não conhece ECharts."""

    model_config = ConfigDict(from_attributes=True)

    t: datetime
    v: float


class ChartSeries(BaseModel):
    """Saída da camada de ETL (backend/etl/device_metrics_etl.py) — série
    temporal de uma métrica já resample'ada e limitada em número de pontos."""

    model_config = ConfigDict(from_attributes=True)

    metric_key: str
    metric_name: str
    unit: str | None
    points: list[ChartPoint]


class AvailabilitySummary(BaseModel):
    """Saída da camada de ETL (backend/etl/availability_etl.py) para um
    device — % de disponibilidade, downtime e MTTR numa janela."""

    model_config = ConfigDict(from_attributes=True)

    device_id: int
    range_hours: int
    availability_pct: float
    downtime_seconds: int
    mttr_seconds: float | None


class PingSweepResultOut(BaseModel):
    """Saída de PingSweepService — quais IPs de uma subnet responderam ICMP.
    Diagnóstico apenas: não identifica MAC, não cria/atualiza Device."""

    subnet: str
    checked: int
    online: list[str]


class DashboardSummary(BaseModel):
    """Saída agregada da camada de ETL para os KPIs da tela de Inventory."""

    model_config = ConfigDict(from_attributes=True)

    total_devices: int
    online: int
    offline: int
    unknown: int
    snmp_supported: int
    avg_availability_pct: float
    open_problems: int
