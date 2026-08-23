import asyncio
import logging
from datetime import UTC, datetime, timedelta

from infra.database.db_connection_handler import db_connection_handler
from repositories.metric_history_repository import MetricHistoryRepository
from repositories.metric_trend_repository import MetricTrendRepository

logger = logging.getLogger(__name__)

TICK_INTERVAL_SECONDS = 900
RAW_RETENTION_DAYS = 7


def run_housekeeping_cycle() -> None:
    """Rollup estilo Zabbix (history/trends/housekeeper): agrega em
    metric_trends toda hora já fechada de metric_history (a hora corrente
    fica de fora — ainda pode receber leituras), depois apaga o bruto mais
    velho que RAW_RETENTION_DAYS. Ordem importa: sempre agrega antes de
    apagar, senão perde dado sem trend correspondente. Chamado em loop por
    run_forever()."""
    now = datetime.now(UTC)
    closed_hour_boundary = now.replace(minute=0, second=0, microsecond=0)
    retention_cutoff = now - timedelta(days=RAW_RETENTION_DAYS)

    with db_connection_handler.get_session() as session:
        MetricTrendRepository(session).upsert_hourly_aggregates(before=closed_hour_boundary)
        MetricHistoryRepository(session).delete_older_than(retention_cutoff)


async def run_forever() -> None:
    """Loop de background separado do de coleta (cadência bem mais longa —
    não faz sentido rodar housekeeping a cada 15s). Mesmo padrão de
    resiliência do registry_metrics_collection: uma falha isolada não pode
    matar essa task pra sempre."""
    while True:
        try:
            run_housekeeping_cycle()
        except Exception:
            logger.exception("run_housekeeping_cycle falhou; tentando de novo no próximo tick")
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
