from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_session
from api.schemas import AvailabilitySummary, ChartSeries, DashboardSummary
from etl.availability_etl import AvailabilityETL
from etl.device_metrics_etl import DeviceMetricsETL
from repositories.device_repository import DeviceRepository

router = APIRouter(tags=["analytics"])

DEFAULT_RANGE_HOURS = 24


def _ensure_device_exists(session: Session, device_id: int) -> None:
    if DeviceRepository(session).get_by_id(device_id) is None:
        raise HTTPException(status_code=404, detail="device não encontrado")


@router.get("/devices/{device_id}/metrics/{metric_key}/series")
def get_metric_series(
    device_id: int,
    metric_key: str,
    range_hours: int = DEFAULT_RANGE_HOURS,
    session: Session = Depends(get_session),
) -> ChartSeries:
    _ensure_device_exists(session, device_id)
    return DeviceMetricsETL(session).build_series(device_id, metric_key, range_hours)


@router.get("/devices/{device_id}/availability")
def get_device_availability(
    device_id: int,
    range_hours: int = DEFAULT_RANGE_HOURS,
    session: Session = Depends(get_session),
) -> AvailabilitySummary:
    _ensure_device_exists(session, device_id)
    return AvailabilityETL(session).summary(device_id, range_hours)


@router.get("/dashboard/summary")
def get_dashboard_summary(
    range_hours: int = DEFAULT_RANGE_HOURS,
    session: Session = Depends(get_session),
) -> DashboardSummary:
    return AvailabilityETL(session).dashboard_summary(range_hours)
