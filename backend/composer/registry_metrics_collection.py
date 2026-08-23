import asyncio
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
    DevicePollResult,
    MetricReading,
    MetricsCollectionService,
)
from services.polling_backoff import next_poll_interval
from services.printer_metrics_service import PrinterMetricsService

TICK_INTERVAL_SECONDS = 15

_NUMERIC_VALUE_TYPES = (MetricValueType.INTEGER, MetricValueType.COUNTER, MetricValueType.GAUGE)


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
        value_text=None if is_numeric else reading.raw_value,
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
        value_text=None if is_numeric else reading.raw_value,
    )


def _apply_result(
    result: DevicePollResult,
    device_status: DeviceStatus,
    device_failures: int,
    device_repo: DeviceRepository,
    event_repo: AvailabilityEventRepository,
    history_repo: MetricHistoryRepository,
    metric_defs_by_id: dict[int, MetricDefinition],
) -> None:
    """Aplica o resultado de UM device: novo status/backoff, transição de
    AvailabilityEvent (se houve mudança de status) e MetricHistory."""
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

    history_repo.save_many(
        [
            _build_history(
                result.device_id,
                checked_at,
                reading,
                metric_defs_by_id[reading.metric_definition_id],
            )
            for reading in result.readings
        ]
    )


async def run_collection_cycle() -> None:
    """Um ciclo de coleta: busca devices com next_poll_at vencido, sonda todos
    em paralelo via SNMP e persiste resultado + eventuais transições de
    status. Chamado em loop por run_forever()."""
    now = datetime.now(UTC)

    with db_connection_handler.get_session() as session:
        device_repo = DeviceRepository(session)
        event_repo = AvailabilityEventRepository(session)
        history_repo = MetricHistoryRepository(session)
        definition_repo = MetricDefinitionRepository(session)
        metric_defs = definition_repo.list_all()
        metric_defs_by_id = {m.id: m for m in metric_defs}

        due_devices = device_repo.list_due_for_poll(now)
        if not due_devices:
            return

        # snapshot antes do poll: record_poll_result vai sobrescrever esses
        # campos no objeto ORM, então precisamos do status/falhas ANTERIORES
        # já capturados pra decidir se houve transição.
        status_before = {d.id: (d.status, d.consecutive_failures) for d in due_devices}

        results = await MetricsCollectionService().execute(due_devices, metric_defs)

        for result in results:
            previous_status, previous_failures = status_before[result.device_id]
            _apply_result(
                result,
                previous_status,
                previous_failures,
                device_repo,
                event_repo,
                history_repo,
                metric_defs_by_id,
            )

        # Métricas dinâmicas (walk) só fazem sentido pra quem respondeu no
        # poll principal — pular device offline evita rodar vários walks
        # contra um IP que já sabemos inalcançável neste ciclo.
        online_ids = {r.device_id for r in results if r.online}
        online_devices = [d for d in due_devices if d.id in online_ids]

        dynamic_results = [
            *await HostResourcesMetricsService().execute(online_devices),
            *await PrinterMetricsService().execute(online_devices),
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
    decidir quem realmente precisa ser sondado agora."""
    while True:
        await run_collection_cycle()
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
