from collections.abc import Iterator

from sqlalchemy.orm import Session

from infra.database.db_connection_handler import db_connection_handler


def get_session() -> Iterator[Session]:
    with db_connection_handler.get_session() as session:
        yield session
