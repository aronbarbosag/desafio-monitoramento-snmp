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
