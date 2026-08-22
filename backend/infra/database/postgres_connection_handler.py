from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .i_connection_strategy import IConnectionStrategy


class PostgresConnectionStrategy(IConnectionStrategy):
    """Strategy concreta: conecta a um Postgres via SQLAlchemy (driver psycopg)."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def create_engine(self) -> Engine:
        # pool_pre_ping evita usar conexões mortas do pool (ex: Postgres derrubou
        # a conexão por timeout) — sem isso a primeira query após ociosidade falha.
        return create_engine(self.database_url, pool_pre_ping=True)

    def create_session_factory(self, engine: Engine) -> sessionmaker[Session]:
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)
