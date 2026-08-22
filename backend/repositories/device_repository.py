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

    def list_all(self) -> list[Device]:
        return self._session.query(Device).all()

    def get_by_id(self, device_id: int) -> Device | None:
        return self._session.get(Device, device_id)

    def list_by_subnet(self, subnet_id: int) -> list[Device]:
        return self._session.query(Device).filter(Device.subnet_id == subnet_id).all()

    def list_due_for_poll(self, now: datetime) -> list[Device]:
        """Devices SNMP-capable (identificados pelo SnmpScanService) cujo
        next_poll_at já venceu — os únicos que o MetricsCollectionService
        sabe como sondar."""
        return (
            self._session.query(Device)
            .filter(Device.snmp_community.isnot(None))
            .filter(Device.next_poll_at <= now)
            .all()
        )

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
    ) -> None:
        """Preenche a identidade SNMP de um Device já existente (encontrado
        primeiro pelo IpScanService), a partir de um SnmpScanResult."""
        device = self._session.get(Device, device_id)
        device.hostname = hostname
        device.sys_descr = sys_descr
        device.sys_object_id = sys_object_id
        device.snmp_community = snmp_community
        self._session.flush()
