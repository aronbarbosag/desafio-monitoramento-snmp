from abc import ABC, abstractmethod

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


class IConnectionStrategy(ABC):
    """Interface genérica (Strategy) para provedores de conexão com banco de dados."""

    @abstractmethod
    def create_engine(self) -> Engine: ...

    @abstractmethod
    def create_session_factory(self, engine: Engine) -> sessionmaker[Session]: ...
