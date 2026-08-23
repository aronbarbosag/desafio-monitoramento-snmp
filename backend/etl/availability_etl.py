from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from models import AvailabilityEvent, DeviceStatus
from repositories.availability_event_repository import AvailabilityEventRepository
from repositories.device_repository import DeviceRepository


@dataclass(frozen=True)
class AvailabilitySummaryResult:
    device_id: int
    range_hours: int
    availability_pct: float
    downtime_seconds: int
    mttr_seconds: float | None


@dataclass(frozen=True)
class DashboardSummaryResult:
    total_devices: int
    online: int
    offline: int
    unknown: int
    snmp_supported: int
    avg_availability_pct: float
    open_problems: int


def _events_frame(
    events: list[AvailabilityEvent], window_start: datetime, window_end: datetime
) -> pd.DataFrame:
    """Clipa cada evento aos limites da janela pedida — um evento pode ter
    começado antes de `window_start` (clip no início) ou ainda estar aberto
    (ended_at nulo vira window_end). `duration` nunca fica negativa mesmo com
    a pequena folga de relógio entre a query e o cálculo."""
    # started_at/ended_at voltam naive do Postgres (coluna sem timezone,
    # sempre gravada em UTC pelo composer) — compara com limites da janela
    # também naive, senão o Python recusa a comparação.
    window_start = window_start.replace(tzinfo=None)
    window_end = window_end.replace(tzinfo=None)
    rows = [
        {
            "device_id": event.device_id,
            "status": event.status,
            "duration": (
                min(event.ended_at or window_end, window_end) - max(event.started_at, window_start)
            ).total_seconds(),
            "closed": event.ended_at is not None,
        }
        for event in events
    ]
    df = pd.DataFrame(rows, columns=["device_id", "status", "duration", "closed"])
    df["duration"] = df["duration"].clip(lower=0)
    return df


class AvailabilityETL:
    """Calcula disponibilidade/downtime/MTTR a partir de AvailabilityEvent —
    etapa ETL do diagrama em backend/docs/fluxo_de_chamadas.png. Overlap de
    intervalo (evento x janela pedida) é o tipo de cálculo que o pandas
    resolve bem vetorizado, principalmente no resumo do dashboard com todos
    os devices de uma vez (uma query, não N)."""

    def __init__(self, session: Session):
        self._session = session

    def summary(self, device_id: int, range_hours: int) -> AvailabilitySummaryResult:
        now = datetime.now(UTC)
        window_start = now - timedelta(hours=range_hours)
        events = AvailabilityEventRepository(self._session).list_by_device_since(
            device_id, window_start
        )

        if not events:
            return AvailabilitySummaryResult(
                device_id=device_id,
                range_hours=range_hours,
                availability_pct=0.0,
                downtime_seconds=0,
                mttr_seconds=None,
            )

        df = _events_frame(events, window_start, now)
        window_seconds = (now - window_start).total_seconds()

        online_seconds = df.loc[df["status"] == DeviceStatus.ONLINE, "duration"].sum()
        offline_seconds = df.loc[df["status"] == DeviceStatus.OFFLINE, "duration"].sum()

        closed_offline = df[(df["status"] == DeviceStatus.OFFLINE) & df["closed"]]
        mttr_seconds = (
            float(closed_offline["duration"].mean()) if not closed_offline.empty else None
        )

        return AvailabilitySummaryResult(
            device_id=device_id,
            range_hours=range_hours,
            availability_pct=round(min(online_seconds / window_seconds * 100, 100.0), 2),
            downtime_seconds=int(offline_seconds),
            mttr_seconds=mttr_seconds,
        )

    def dashboard_summary(self, range_hours: int) -> DashboardSummaryResult:
        now = datetime.now(UTC)
        window_start = now - timedelta(hours=range_hours)

        devices = DeviceRepository(self._session).list_all()
        events = AvailabilityEventRepository(self._session).list_since(window_start)

        total_devices = len(devices)
        online = sum(1 for d in devices if d.status == DeviceStatus.ONLINE)
        offline = sum(1 for d in devices if d.status == DeviceStatus.OFFLINE)
        unknown = sum(1 for d in devices if d.status == DeviceStatus.UNKNOWN)
        snmp_supported = sum(1 for d in devices if d.snmp_supported)
        open_problems = sum(
            1 for e in events if e.ended_at is None and e.status == DeviceStatus.OFFLINE
        )

        if not events:
            avg_availability_pct = 0.0
        else:
            df = _events_frame(events, window_start, now)
            window_seconds = (now - window_start).total_seconds()
            # reindex: device com só evento OFFLINE não aparece no groupby de
            # ONLINE — sem isso, ele seria ignorado da média em vez de contar
            # como 0% (mean() de uma série menor infla a média geral).
            device_ids_with_events = df["device_id"].unique()
            online_by_device = (
                df[df["status"] == DeviceStatus.ONLINE]
                .groupby("device_id")["duration"]
                .sum()
                .reindex(device_ids_with_events, fill_value=0)
            )
            pct_by_device = (online_by_device / window_seconds * 100).clip(upper=100)
            avg_availability_pct = float(pct_by_device.mean()) if not pct_by_device.empty else 0.0

        return DashboardSummaryResult(
            total_devices=total_devices,
            online=online,
            offline=offline,
            unknown=unknown,
            snmp_supported=snmp_supported,
            avg_availability_pct=round(avg_availability_pct, 2),
            open_problems=open_problems,
        )
