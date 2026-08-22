from sqlalchemy.orm import Session

from models.device import Device


class DeviceRepository:
    """Acesso a dados da entidade Device."""

    def __init__(self, session: Session):
        self._session = session

    def save_many(self, devices: list[Device]) -> list[Device]:
        self._session.add_all(devices)
        self._session.flush()
        return devices

    def list_by_subnet(self, subnet_id: int) -> list[Device]:
        return self._session.query(Device).filter(Device.subnet_id == subnet_id).all()

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
