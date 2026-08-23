import os

# Testes sempre usam o Postgres descartável do docker-compose.test.yml, nunca
# o Supabase (produção) — setado ANTES de importar infra.database, cujo
# db_connection_handler é um singleton criado no import (lê DATABASE_URL uma
# vez só). load_dotenv() (settings/config.py) não sobrescreve uma env var já
# setada, então isso vence o valor do .env.
os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost:5433/test"
os.environ.setdefault("DISABLE_BACKGROUND_POLLING", "1")

from collections.abc import Iterator

import pytest
from sqlalchemy import text

from infra.database.db_connection_handler import db_connection_handler
from models import Base


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> None:
    Base.metadata.create_all(db_connection_handler.get_engine())


@pytest.fixture(autouse=True)
def _reset_db(_create_schema: None) -> Iterator[None]:
    """Zera todas as tabelas antes de cada teste (TRUNCATE ... CASCADE).

    Bem mais simples e robusto que transação com rollback compartilhada entre
    threads: Starlette roda Depends() síncronos (ex: get_session) numa
    threadpool, então uma Connection/Session do SQLAlchemy compartilhada
    entre threads corrompe a pilha de SAVEPOINT (tentado e abandonado). Como
    aqui é um Postgres 100% descartável só pra teste (docker-compose.test.yml,
    dado em tmpfs), TRUNCATE puro e sem monkeypatch é suficiente — cada
    get_session() continua pegando uma connection nova do pool, como em
    produção."""
    with db_connection_handler.get_session() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))
    yield
