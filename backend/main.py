import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from api.routers.devices import router as devices_router
from composer.registry_metric_catalog import seed_metric_catalog
from composer.registry_metrics_collection import run_forever
from infra.database.db_connection_handler import db_connection_handler
from models import Base
from settings.config import DISABLE_BACKGROUND_POLLING


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(db_connection_handler.get_engine())
    seed_metric_catalog()
    collection_task = None if DISABLE_BACKGROUND_POLLING else asyncio.create_task(run_forever())
    yield
    if collection_task is not None:
        collection_task.cancel()
        with suppress(asyncio.CancelledError):
            await collection_task
    db_connection_handler.close()


app = FastAPI(title="SNMP Monitor", lifespan=lifespan)
app.include_router(devices_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
