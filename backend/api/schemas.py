from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models import DeviceStatus, MetricHistory, MetricValueType


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip: str
    mac: str
    vendor: str | None
    hostname: str | None
    sys_descr: str | None
    model_name: str | None
    sys_contact: str | None
    sys_location: str | None
    status: DeviceStatus
    poll_interval_seconds: int
    consecutive_failures: int
    last_checked_at: datetime | None


class MetricHistoryOut(BaseModel):
    id: int
    collected_at: datetime
    metric_key: str
    metric_name: str
    metric_unit: str | None
    value_type: MetricValueType
    value_numeric: float | None
    value_text: str | None

    @classmethod
    def from_model(cls, history: MetricHistory) -> "MetricHistoryOut":
        return cls(
            id=history.id,
            collected_at=history.collected_at,
            metric_key=history.metric_definition.key,
            metric_name=history.metric_definition.name,
            metric_unit=history.metric_definition.unit,
            value_type=history.metric_definition.value_type,
            value_numeric=history.value_numeric,
            value_text=history.value_text,
        )


class AvailabilityEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: DeviceStatus
    started_at: datetime
    ended_at: datetime | None


class ScanResult(BaseModel):
    subnet: str | None
    devices_found: int
    devices_probed: int
    snmp_identified: int
