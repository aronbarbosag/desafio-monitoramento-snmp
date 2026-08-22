from sqlalchemy.orm import Session

from models.subnet import Subnet


class SubnetRepository:
    """Acesso a dados da entidade Subnet."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, subnet: Subnet) -> Subnet:
        self._session.add(subnet)
        self._session.flush()
        return subnet

    def list_all(self) -> list[Subnet]:
        return self._session.query(Subnet).all()
