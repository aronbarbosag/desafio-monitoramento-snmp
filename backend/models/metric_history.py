from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .device import Device
    from .metric_definition import MetricDefinition


class MetricHistory(Base):
    """Série bruta de valores coletados via SNMP pelo MetricsCollectionService.

    Tabela quente e append-only — o índice composto cobre tanto "último valor
    de um device" quanto "range de tempo para gráfico", sem precisar de tabelas
    de rollup (deixadas como evolução futura, fora do escopo deste desafio)."""

    __tablename__ = "metric_history"
    __table_args__ = (
        Index(
            "ix_metric_history_device_metric_time",
            "device_id",
            "metric_definition_id",
            "collected_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    device: Mapped["Device"] = relationship()

    metric_definition_id: Mapped[int] = mapped_column(ForeignKey("metric_definitions.id"))
    metric_definition: Mapped["MetricDefinition"] = relationship()

    collected_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    value_numeric: Mapped[float | None] = mapped_column(nullable=True)
    value_text: Mapped[str | None] = mapped_column(nullable=True)
