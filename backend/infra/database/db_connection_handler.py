from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from settings.config import DATABASE_URL

from .i_connection_strategy import IConnectionStrategy
from .postgres_connection_handler import PostgresConnectionStrategy
from .sqlite_connection_handler import SQLiteConnectionStrategy


class DatabaseConnectionHandler:
    """
    Facade que centraliza o gerenciamento da conexão com o banco de dados.

    Esconde a criação de engine/sessão por trás de uma interface simples.
    A estratégia concreta de conexão (SQLite, e futuramente outras) é
    injetada via IConnectionStrategy, seguindo o padrão Strategy.
    """

    def __init__(self, strategy: IConnectionStrategy):
        self._strategy = strategy
        self._engine = strategy.create_engine()
        self._session_factory = strategy.create_session_factory(self._engine)

    def get_engine(self) -> Engine:
        return self._engine

    @contextmanager
    def get_session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        self._engine.dispose()


def _default_strategy() -> IConnectionStrategy:
    """Postgres se DATABASE_URL estiver configurada, senão SQLite local."""
    if DATABASE_URL:
        return PostgresConnectionStrategy(DATABASE_URL)
    return SQLiteConnectionStrategy()


db_connection_handler = DatabaseConnectionHandler(_default_strategy())
