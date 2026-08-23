import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.analytics import router as analytics_router
from api.routers.devices import router as devices_router
from composer.registry_history_housekeeping import run_forever as run_housekeeping_forever
from composer.registry_metric_catalog import seed_metric_catalog
from composer.registry_metrics_collection import run_forever as run_collection_forever
from infra.database.db_connection_handler import db_connection_handler
from models import Base
from settings.config import CORS_ALLOWED_ORIGINS, DISABLE_BACKGROUND_POLLING


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(db_connection_handler.get_engine())
    seed_metric_catalog()
    background_tasks = (
        []
        if DISABLE_BACKGROUND_POLLING
        else [
            asyncio.create_task(run_collection_forever()),
            asyncio.create_task(run_housekeeping_forever()),
        ]
    )
    yield
    for task in background_tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    db_connection_handler.close()


app = FastAPI(title="SNMP Monitor", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(devices_router)
app.include_router(analytics_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
