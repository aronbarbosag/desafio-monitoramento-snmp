from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import MetricValueType


class MetricDefinition(Base):
    """Catálogo de métricas coletáveis via SNMP — o 'template' do Zabbix como
    dado (linha de tabela), não como código, para crescer sem precisar de deploy."""

    __tablename__ = "metric_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 255, não 64: chaves de métricas dinâmicas nascem de um slug do nome do
    # device/interface (ver DynamicMetricReading) — interfaces virtuais do
    # Windows (Hyper-V) geram nomes bem mais longos que os ~20 chars de uma
    # interface física comum.
    key: Mapped[str] = mapped_column(String(255), unique=True)
    oid: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value_type: Mapped[MetricValueType] = mapped_column(
        SAEnum(MetricValueType, native_enum=False, length=16),
    )
