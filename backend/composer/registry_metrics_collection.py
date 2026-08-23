import asyncio
import logging
from datetime import UTC, datetime, timedelta

from infra.database.db_connection_handler import db_connection_handler
from models import DeviceStatus, MetricDefinition, MetricHistory, MetricValueType
from repositories.availability_event_repository import AvailabilityEventRepository
from repositories.device_repository import DeviceRepository
from repositories.metric_definition_repository import MetricDefinitionRepository
from repositories.metric_history_repository import MetricHistoryRepository
from services.dynamic_metric_reading import DynamicMetricReading
from services.host_resources_metrics_service import HostResourcesMetricsService
from services.metrics_collection_service import (
    MetricReading,
    MetricsCollectionService,
)
from services.ping_service import PingResult, PingService
from services.polling_backoff import next_poll_interval
from services.printer_metrics_service import PrinterMetricsService

logger = logging.getLogger(__name__)

TICK_INTERVAL_SECONDS = 15

_NUMERIC_VALUE_TYPES = (MetricValueType.INTEGER, MetricValueType.COUNTER, MetricValueType.GAUGE)


def _sanitize_text(raw_value: str) -> str:
    """Alguns OIDs (ex: hrPrinterDetectedErrorState) são bitmask retornados
    como OCTET STRING — podem conter bytes NUL, que o Postgres rejeita em
    coluna de texto (SQLite aceitava, por isso só apareceu ao trocar de
    banco). Remove-los é seguro aqui: o dado é um bitmask de erro, all-zero
    (string vazia após o strip) já significa "sem erro"."""
    return raw_value.replace("\x00", "")


def _build_history(
    device_id: int,
    collected_at: datetime,
    reading: MetricReading,
    metric_def: MetricDefinition,
) -> MetricHistory:
    """Guarda o valor bruto (sempre string, vindo do pysnmp) na coluna certa
    conforme o tipo declarado no catálogo — numérico pra contadores/gauges,
    texto pro resto."""
    is_numeric = metric_def.value_type in _NUMERIC_VALUE_TYPES
    return MetricHistory(
        device_id=device_id,
        metric_definition_id=metric_def.id,
        collected_at=collected_at,
        value_numeric=float(reading.raw_value) if is_numeric else None,
        value_text=None if is_numeric else _sanitize_text(reading.raw_value),
    )


def _build_dynamic_history(
    device_id: int,
    collected_at: datetime,
    reading: DynamicMetricReading,
    definition_repo: MetricDefinitionRepository,
) -> MetricHistory:
    """Como _build_history, mas a MetricDefinition é descoberta em runtime
    (chave/tipo vêm do walk, não do catálogo estático) — get_or_create garante
    idempotência entre ciclos e entre devices que reportam a mesma métrica
    (ex: dois devices com uma interface chamada "eth0")."""
    definition = definition_repo.get_or_create(
        reading.key, name=reading.name, value_type=reading.value_type, unit=reading.unit
    )
    is_numeric = reading.value_type in _NUMERIC_VALUE_TYPES
    return MetricHistory(
        device_id=device_id,
        metric_definition_id=definition.id,
        collected_at=collected_at,
        value_numeric=float(reading.raw_value) if is_numeric else None,
        value_text=None if is_numeric else _sanitize_text(reading.raw_value),
    )


def _apply_ping_result(
    result: PingResult,
    device_status: DeviceStatus,
    device_failures: int,
    device_repo: DeviceRepository,
    event_repo: AvailabilityEventRepository,
) -> None:
    """Aplica o resultado do ping de UM device: novo status/backoff e
    transição de AvailabilityEvent (se houve mudança de status). O ping é a
    única fonte de status agora — cobre devices com e sem SNMP igualmente."""
    new_status = DeviceStatus.ONLINE if result.online else DeviceStatus.OFFLINE
    consecutive_failures = 0 if result.online else device_failures + 1
    poll_interval = next_poll_interval(consecutive_failures)
    checked_at = datetime.now(UTC)

    device_repo.record_poll_result(
        result.device_id,
        status=new_status,
        consecutive_failures=consecutive_failures,
        poll_interval_seconds=poll_interval,
        next_poll_at=checked_at + timedelta(seconds=poll_interval),
        last_checked_at=checked_at,
    )

    if new_status != device_status:
        event_repo.close_open_event(result.device_id, ended_at=checked_at)
        event_repo.open_event(result.device_id, status=new_status, started_at=checked_at)


async def run_collection_cycle() -> None:
    """Um ciclo de coleta: busca devices com next_poll_at vencido, decide
    status via ping (todos os devices, SNMP ou não) e, pra quem tem SNMP e
    respondeu ao ping, coleta métricas em cima disso. Chamado em loop por
    run_forever()."""
    now = datetime.now(UTC)

    with db_connection_handler.get_session() as session:
        device_repo = DeviceRepository(session)
        event_repo = AvailabilityEventRepository(session)
        history_repo = MetricHistoryRepository(session)
        definition_repo = MetricDefinitionRepository(session)
        metric_defs = definition_repo.list_static()
        metric_defs_by_id = {m.id: m for m in metric_defs}

        due_devices = device_repo.list_due_for_poll(now)
        if not due_devices:
            return

        # snapshot antes do ping: record_poll_result vai sobrescrever esses
        # campos no objeto ORM, então precisamos do status/falhas ANTERIORES
        # já capturados pra decidir se houve transição.
        status_before = {d.id: (d.status, d.consecutive_failures) for d in due_devices}

        ping_results = await PingService().execute(due_devices)

        for result in ping_results:
            previous_status, previous_failures = status_before[result.device_id]
            _apply_ping_result(result, previous_status, previous_failures, device_repo, event_repo)

        # SNMP (métricas do catálogo + walks dinâmicos) só faz sentido pra
        # quem tem snmp_supported E respondeu ao ping neste ciclo.
        online_ids = {r.device_id for r in ping_results if r.online}
        online_snmp_devices = [d for d in due_devices if d.id in online_ids and d.snmp_supported]

        snmp_results = await MetricsCollectionService().execute(online_snmp_devices, metric_defs)
        snmp_collected_at = datetime.now(UTC)
        history_repo.save_many(
            [
                _build_history(
                    result.device_id,
                    snmp_collected_at,
                    reading,
                    metric_defs_by_id[reading.metric_definition_id],
                )
                for result in snmp_results
                for reading in result.readings
            ]
        )

        dynamic_results = [
            *await HostResourcesMetricsService().execute(online_snmp_devices),
            *await PrinterMetricsService().execute(online_snmp_devices),
        ]
        dynamic_collected_at = datetime.now(UTC)
        history_repo.save_many(
            [
                _build_dynamic_history(
                    result.device_id, dynamic_collected_at, reading, definition_repo
                )
                for result in dynamic_results
                for reading in result.readings
            ]
        )


async def run_forever() -> None:
    """Loop de background simples (sem APScheduler, por decisão de escopo):
    tenta um ciclo a cada TICK_INTERVAL_SECONDS, deixando list_due_for_poll
    decidir quem realmente precisa ser sondado agora.

    Uma exceção não tratada em UM ciclo não pode derrubar essa task pra
    sempre (asyncio.create_task não é aguardada por ninguém, então a task
    simplesmente morre em silêncio) — por isso o try/except aqui: loga e
    tenta de novo no próximo tick, em vez de travar todo status em UNKNOWN
    até a aplicação ser reiniciada."""
    while True:
        try:
            await run_collection_cycle()
        except Exception:
            logger.exception("run_collection_cycle falhou; tentando de novo no próximo tick")
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
