from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import DeviceStatus

if TYPE_CHECKING:
    from .subnet import Subnet


class Device(Base):
    """Um dispositivo encontrado pelo IpScanService (ip, mac e fabricante),
    com sua identidade SNMP e estado de polling quando monitorado."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip: Mapped[str] = mapped_column(String(15))
    mac: Mapped[str] = mapped_column(String(17))
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)

    subnet_id: Mapped[int] = mapped_column(ForeignKey("subnets.id"))
    subnet: Mapped["Subnet"] = relationship(back_populates="devices")

    # Identidade SNMP, preenchida pelo SnmpScanService quando o device responde.
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sys_descr: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sys_object_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snmp_community: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Estado de polling, usado pelo MetricsCollectionService (backoff exponencial
    # em cima de next_poll_at/consecutive_failures quando o device não responde).
    status: Mapped[DeviceStatus] = mapped_column(
        SAEnum(DeviceStatus, native_enum=False, length=16),
        default=DeviceStatus.UNKNOWN,
    )
    poll_interval_seconds: Mapped[int] = mapped_column(default=60)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    next_poll_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
