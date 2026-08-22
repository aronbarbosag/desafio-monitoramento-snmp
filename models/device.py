from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .subnet import Subnet


class Device(Base):
    """Um dispositivo encontrado pelo IpScanService (ip, mac e fabricante)."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip: Mapped[str] = mapped_column(String(15))
    mac: Mapped[str] = mapped_column(String(17))
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)

    subnet_id: Mapped[int] = mapped_column(ForeignKey("subnets.id"))
    subnet: Mapped["Subnet"] = relationship(back_populates="devices")
