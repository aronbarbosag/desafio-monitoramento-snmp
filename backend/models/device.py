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
    # unique: identidade física do device — IP muda por DHCP, mac não. Evita
    # que cada scan crie uma linha nova pro mesmo aparelho (ver
    # DeviceRepository.upsert_many). Nullable: devices achados via
    # PingSweepService (ICMP/L3, usado quando o ARP não tem acesso à LAN
    # física — ex: dentro do Docker) não têm como saber o MAC; nesse caso o
    # dedup cai pro IP dentro da mesma subnet. Postgres/SQLite não tratam
    # múltiplos NULL como duplicata de UNIQUE, então vários devices sem mac
    # convivem numa mesma tabela sem violar a constraint.
    mac: Mapped[str | None] = mapped_column(String(17), unique=True, nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Categoria do device (ex: "CELULAR", "SMART TV", "ROTEADOR") — nenhum
    # scan preenche isso automaticamente, é classificação manual do usuário.
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    subnet_id: Mapped[int] = mapped_column(ForeignKey("subnets.id"))
    subnet: Mapped["Subnet"] = relationship(back_populates="devices")

    # Identidade SNMP, preenchida pelo SnmpScanService quando o device responde.
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sys_descr: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sys_object_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snmp_community: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Setado junto com snmp_community em update_snmp_info, quando o device
    # responde ao probe do SnmpScanService — sinal explícito e persistido de
    # suporte a SNMP (em vez de inferir por snmp_community.isnot(None)).
    snmp_supported: Mapped[bool] = mapped_column(default=False)
    # Modelo (ex: "L3250 Series"), vindo de prtGeneralPrinterName quando o
    # device suporta Printer MIB. Setado != None é o sinal usado pelo
    # PrinterMetricsService pra saber quais devices vale a pena sondar.
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # sysContact/sysLocation (MIB-2 System) — metadado administrativo que o
    # próprio device reporta (responsável, localização física). Muitos
    # devices deixam em branco; nesse caso fica None.
    sys_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sys_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

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
