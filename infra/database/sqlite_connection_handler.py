from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from settings.config import DB_PATH

from .i_connection_strategy import IConnectionStrategy


class SQLiteConnectionStrategy(IConnectionStrategy):
    """Strategy concreta: conecta a um arquivo SQLite local via SQLAlchemy."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def create_engine(self) -> Engine:
        # check_same_thread=False porque o handler pode ser usado a partir de
        # threads diferentes (ex: asyncio.to_thread) durante a vida da aplicação.
        return create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )

    def create_session_factory(self, engine: Engine) -> sessionmaker[Session]:
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)
