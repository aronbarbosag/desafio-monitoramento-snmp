from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infra.database.db_connection_handler import db_connection_handler
from models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(db_connection_handler.get_engine())
    yield
    db_connection_handler.close()


app = FastAPI(title="SNMP Monitor", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
