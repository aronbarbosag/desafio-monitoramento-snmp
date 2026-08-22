import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from composer.registry_metric_catalog import seed_metric_catalog
from composer.registry_metrics_collection import run_forever
from infra.database.db_connection_handler import db_connection_handler
from models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(db_connection_handler.get_engine())
    seed_metric_catalog()
    collection_task = asyncio.create_task(run_forever())
    yield
    collection_task.cancel()
    with suppress(asyncio.CancelledError):
        await collection_task
    db_connection_handler.close()


app = FastAPI(title="SNMP Monitor", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
