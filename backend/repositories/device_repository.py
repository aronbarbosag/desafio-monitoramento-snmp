from datetime import datetime

from sqlalchemy.orm import Session

from models.device import Device
from models.enums import DeviceStatus


class DeviceRepository:
    """Acesso a dados da entidade Device."""

    def __init__(self, session: Session):
        self._session = session

    def save_many(self, devices: list[Device]) -> list[Device]:
        self._session.add_all(devices)
        self._session.flush()
        return devices

    def upsert_many(self, devices: list[Device]) -> list[Device]:
        """Como save_many, mas casando por identidade: quando o device tem
        mac (IpScanService/ARP), casa por mac — a identidade física do
        aparelho (IP não é, muda por DHCP). Sem mac (PingSweepService/ICMP,
        usado quando o ARP não enxerga a LAN física — ex: dentro do Docker),
        casa por ip dentro da mesma subnet: best-effort, já que sem MAC não
        há como reconhecer o mesmo aparelho depois de um DHCP renovar o IP.
        Em ambos os casos, atualiza a linha existente em vez de criar uma
        nova — preserva status/backoff/identidade SNMP."""
        result = []
        for incoming in devices:
            if incoming.mac is not None:
                existing = self._session.query(Device).filter_by(mac=incoming.mac).one_or_none()
            else:
                existing = (
                    self._session.query(Device)
                    .filter_by(ip=incoming.ip, subnet_id=incoming.subnet_id, mac=None)
                    .one_or_none()
                )
            if existing is None:
                self._session.add(incoming)
                result.append(incoming)
                continue
            existing.ip = incoming.ip
            existing.vendor = incoming.vendor
            existing.subnet_id = incoming.subnet_id
            result.append(existing)
        self._session.flush()
        return result

    def list_all(self) -> list[Device]:
        return self._session.query(Device).all()

    def get_by_id(self, device_id: int) -> Device | None:
        return self._session.get(Device, device_id)

    def list_by_subnet(self, subnet_id: int) -> list[Device]:
        return self._session.query(Device).filter(Device.subnet_id == subnet_id).all()

    def list_due_for_poll(self, now: datetime) -> list[Device]:
        """Todo device (SNMP-capable ou não) cujo next_poll_at já venceu —
        o PingService sabe sondar qualquer um; só quem tem snmp_supported
        também passa pelo MetricsCollectionService."""
        return self._session.query(Device).filter(Device.next_poll_at <= now).all()

    def record_poll_result(
        self,
        device_id: int,
        *,
        status: DeviceStatus,
        consecutive_failures: int,
        poll_interval_seconds: int,
        next_poll_at: datetime,
        last_checked_at: datetime,
    ) -> None:
        """Aplica o resultado de um poll (sucesso ou falha) ao estado do
        device — status, backoff e agendamento do próximo poll."""
        device = self._session.get(Device, device_id)
        device.status = status
        device.consecutive_failures = consecutive_failures
        device.poll_interval_seconds = poll_interval_seconds
        device.next_poll_at = next_poll_at
        device.last_checked_at = last_checked_at
        self._session.flush()

    def update_snmp_info(
        self,
        device_id: int,
        *,
        hostname: str,
        sys_descr: str,
        sys_object_id: str,
        snmp_community: str,
        model_name: str | None = None,
        sys_contact: str | None = None,
        sys_location: str | None = None,
    ) -> None:
        """Preenche a identidade SNMP de um Device já existente (encontrado
        primeiro pelo IpScanService), a partir de um SnmpScanResult."""
        device = self._session.get(Device, device_id)
        device.hostname = hostname
        device.sys_descr = sys_descr
        device.sys_object_id = sys_object_id
        device.snmp_community = snmp_community
        device.snmp_supported = True
        device.model_name = model_name
        device.sys_contact = sys_contact
        device.sys_location = sys_location
        self._session.flush()
