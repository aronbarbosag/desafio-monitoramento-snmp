from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .device import Device
    from .metric_definition import MetricDefinition


class MetricTrend(Base):
    """Agregado por hora de metric_history (min/max/avg/count) — mesmo padrão
    do Zabbix (history vs trends): metric_history vira janela curta (ver
    RAW_RETENTION_DAYS em registry_history_housekeeping.py), aqui fica o
    resumo de longo prazo que sustenta gráfico de tendência sem o bruto
    crescer sem limite. Só métricas numéricas geram trend — texto (ex: status
    de impressora) só existe no histórico bruto, igual history_str no Zabbix."""

    __tablename__ = "metric_trends"
    __table_args__ = (
        UniqueConstraint(
            "device_id", "metric_definition_id", "bucket_start", name="uq_metric_trends_bucket"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    device: Mapped["Device"] = relationship()

    metric_definition_id: Mapped[int] = mapped_column(ForeignKey("metric_definitions.id"))
    metric_definition: Mapped["MetricDefinition"] = relationship()

    bucket_start: Mapped[datetime]
    value_min: Mapped[float]
    value_max: Mapped[float]
    value_avg: Mapped[float]
    sample_count: Mapped[int]
