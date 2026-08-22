from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_session
from api.schemas import AvailabilityEventOut, DeviceOut, MetricHistoryOut, ScanResult
from composer.registry_devices import ScanSummary, run_ip_and_snmp_scan
from repositories.availability_event_repository import AvailabilityEventRepository
from repositories.device_repository import DeviceRepository
from repositories.metric_history_repository import MetricHistoryRepository

router = APIRouter(prefix="/devices", tags=["devices"])

DEFAULT_LIST_LIMIT = 100


def _get_device_or_404(device_repo: DeviceRepository, device_id: int):
    device = device_repo.get_by_id(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device não encontrado")
    return device


@router.get("")
def list_devices(session: Session = Depends(get_session)) -> list[DeviceOut]:
    return DeviceRepository(session).list_all()


@router.get("/{device_id}")
def get_device(device_id: int, session: Session = Depends(get_session)) -> DeviceOut:
    return _get_device_or_404(DeviceRepository(session), device_id)


@router.get("/{device_id}/history")
def get_device_history(
    device_id: int,
    limit: int = DEFAULT_LIST_LIMIT,
    session: Session = Depends(get_session),
) -> list[MetricHistoryOut]:
    _get_device_or_404(DeviceRepository(session), device_id)
    history = MetricHistoryRepository(session).list_by_device(device_id, limit)
    return [MetricHistoryOut.from_model(h) for h in history]


@router.get("/{device_id}/events")
def get_device_events(
    device_id: int,
    limit: int = DEFAULT_LIST_LIMIT,
    session: Session = Depends(get_session),
) -> list[AvailabilityEventOut]:
    _get_device_or_404(DeviceRepository(session), device_id)
    return AvailabilityEventRepository(session).list_by_device(device_id, limit)


@router.post("/scan")
async def scan_devices(summary: ScanSummary = Depends(run_ip_and_snmp_scan)) -> ScanResult:
    return ScanResult(
        subnet=summary.subnet,
        devices_found=summary.devices_found,
        devices_probed=summary.devices_probed,
        snmp_identified=summary.snmp_identified,
    )
