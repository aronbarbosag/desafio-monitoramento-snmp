from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .device import Device


class Subnet(Base):
    """Uma execução do IpScanService sobre uma subnet (ex: '192.168.1.0/24')."""

    __tablename__ = "subnets"

    id: Mapped[int] = mapped_column(primary_key=True)
    cidr: Mapped[str] = mapped_column(String(18), index=True)
    scanned_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
    )

    devices: Mapped[list["Device"]] = relationship(
        back_populates="subnet",
        cascade="all, delete-orphan",
    )
